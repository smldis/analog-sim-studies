#include <stdio.h>
#include <string.h>
#include <ctype.h>

#define MAX_LINE 8192
#define MAX_PENDING 3
#define MAX_PATH_LEN 1024

typedef enum {
    ST_OUTSIDE = 0,
    ST_INSIDE_SUBCKT,
    ST_AFTER_ENDS
} State;

typedef struct {
    char lines[MAX_PENDING][MAX_LINE];
    long line_no[MAX_PENDING];
    int count;
} PendingBuffer;

typedef struct {
    const char *input_path;
    const char *main_out_path;
    const char *subckt_out_path;
    const char *include_name;
} ExtractOptions;

typedef struct {
    long input_line_no;
    char message[256];
} ExtractError;

/* ---------- utility ---------- */

static const char *skip_ws(const char *s) {
    while (*s && isspace((unsigned char)*s)) {
        s++;
    }
    return s;
}

static int is_blank_line(const char *s) {
    s = skip_ws(s);
    return (*s == '\0');
}

static int is_comment_line(const char *s) {
    s = skip_ws(s);
    return (*s == '*');
}

static int starts_with_three_stars(const char *line) {
    const char *p = skip_ws(line);
    return (strncmp(p, "***", 3) == 0);
}

static int starts_with_kw_icase(const char *line, const char *kw) {
    const char *p = skip_ws(line);
    size_t i;

    if (is_comment_line(p)) {
        return 0;
    }

    for (i = 0; kw[i] != '\0'; i++) {
        if (tolower((unsigned char)p[i]) != tolower((unsigned char)kw[i])) {
            return 0;
        }
    }

    if (p[i] != '\0' && !isspace((unsigned char)p[i])) {
        return 0;
    }

    return 1;
}

static int safe_copy_line(char *dst, size_t dst_size, const char *src) {
    size_t n = strlen(src);
    if (n + 1 > dst_size) {
        return -1;
    }
    memcpy(dst, src, n + 1);
    return 0;
}

static void set_error(ExtractError *err, long line_no, const char *msg) {
    if (!err) {
        return;
    }
    err->input_line_no = line_no;
    snprintf(err->message, sizeof(err->message), "%s", msg);
}

static int write_pending(FILE *out, PendingBuffer *pb) {
    int i;
    for (i = 0; i < pb->count; i++) {
        if (fputs(pb->lines[i], out) == EOF) {
            return -1;
        }
    }
    pb->count = 0;
    return 0;
}

static void clear_pending(PendingBuffer *pb) {
    pb->count = 0;
}

static int append_pending_strict(PendingBuffer *pb,
                                 const char *line,
                                 long line_no,
                                 ExtractError *err)
{
    if (pb->count >= MAX_PENDING) {
        set_error(err, line_no,
                  "more than 3 pre-.SUBCKT context lines detected");
        return -1;
    }

    if (safe_copy_line(pb->lines[pb->count], sizeof(pb->lines[pb->count]), line) != 0) {
        set_error(err, line_no, "input line exceeds pending buffer capacity");
        return -1;
    }

    pb->line_no[pb->count] = line_no;
    pb->count++;
    return 0;
}

static int copy_stream(FILE *in, FILE *out) {
    char line[MAX_LINE];

    while (fgets(line, sizeof(line), in) != NULL) {
        if (fputs(line, out) == EOF) {
            return -1;
        }
    }

    if (ferror(in)) {
        return -1;
    }

    return 0;
}

static int line_was_truncated(const char *line) {
    size_t n = strlen(line);
    if (n == 0) {
        return 0;
    }
    return (line[n - 1] != '\n');
}

static void close_if_open(FILE **fp) {
    if (*fp) {
        fclose(*fp);
        *fp = NULL;
    }
}

static void cleanup_file(const char *path) {
    if (path && *path) {
        remove(path);
    }
}

/* ---------- main extraction ---------- */

int extract_subckts_strict(const ExtractOptions *opt, ExtractError *err) {
    FILE *in = NULL;
    FILE *main_tmp = NULL;
    FILE *sub_tmp = NULL;
    FILE *main_tmp_read = NULL;
    FILE *main_out = NULL;
    FILE *sub_out = NULL;

    char line[MAX_LINE];
    char main_tmp_path[MAX_PATH_LEN];
    char sub_tmp_path[MAX_PATH_LEN];

    long input_line_no = 0;
    int include_inserted = 0;
    State state = ST_OUTSIDE;
    PendingBuffer pending;

    pending.count = 0;

    if (!opt || !opt->input_path || !opt->main_out_path || !opt->subckt_out_path || !opt->include_name) {
        set_error(err, 0, "invalid arguments");
        return -1;
    }

    if (snprintf(main_tmp_path, sizeof(main_tmp_path), "%s.tmp", opt->main_out_path) >= (int)sizeof(main_tmp_path)) {
        set_error(err, 0, "main temp path too long");
        return -1;
    }

    if (snprintf(sub_tmp_path, sizeof(sub_tmp_path), "%s.tmp", opt->subckt_out_path) >= (int)sizeof(sub_tmp_path)) {
        set_error(err, 0, "subckt temp path too long");
        return -1;
    }

    in = fopen(opt->input_path, "r");
    if (!in) {
        set_error(err, 0, "cannot open input file");
        return -1;
    }

    main_tmp = fopen(main_tmp_path, "w");
    if (!main_tmp) {
        set_error(err, 0, "cannot open main temp output file");
        goto fail;
    }

    sub_tmp = fopen(sub_tmp_path, "w");
    if (!sub_tmp) {
        set_error(err, 0, "cannot open subckt temp output file");
        goto fail;
    }

    while (fgets(line, sizeof(line), in) != NULL) {
        input_line_no++;

        if (line_was_truncated(line)) {
            set_error(err, input_line_no, "input line exceeds MAX_LINE");
            goto fail;
        }

        switch (state) {
        case ST_OUTSIDE:
            if (is_blank_line(line) || starts_with_three_stars(line)) {
                if (append_pending_strict(&pending, line, input_line_no, err) != 0) {
                    goto fail;
                }
            } else if (starts_with_kw_icase(line, ".SUBCKT")) {
                if (!include_inserted) {
                    if (fprintf(main_tmp, ".INCLUDE \"%s\"\n", opt->include_name) < 0) {
                        set_error(err, input_line_no, "write error on main temp file");
                        goto fail;
                    }
                    include_inserted = 1;
                }

                if (write_pending(sub_tmp, &pending) != 0) {
                    set_error(err, input_line_no, "write error on subckt temp file");
                    goto fail;
                }

                if (fputs(line, sub_tmp) == EOF) {
                    set_error(err, input_line_no, "write error on subckt temp file");
                    goto fail;
                }

                state = ST_INSIDE_SUBCKT;
            } else {
                if (write_pending(main_tmp, &pending) != 0) {
                    set_error(err, input_line_no, "write error on main temp file");
                    goto fail;
                }

                if (fputs(line, main_tmp) == EOF) {
                    set_error(err, input_line_no, "write error on main temp file");
                    goto fail;
                }
            }
            break;

        case ST_INSIDE_SUBCKT:
            if (starts_with_kw_icase(line, ".SUBCKT")) {
                set_error(err, input_line_no, "nested .SUBCKT detected");
                goto fail;
            }

            if (fputs(line, sub_tmp) == EOF) {
                set_error(err, input_line_no, "write error on subckt temp file");
                goto fail;
            }

            if (starts_with_kw_icase(line, ".ENDS")) {
                state = ST_AFTER_ENDS;
            }
            break;

        case ST_AFTER_ENDS:
            if (is_blank_line(line) || starts_with_three_stars(line)) {
                if (fputs(line, sub_tmp) == EOF) {
                    set_error(err, input_line_no, "write error on subckt temp file");
                    goto fail;
                }
            } else if (starts_with_kw_icase(line, ".SUBCKT")) {
                if (fputs(line, sub_tmp) == EOF) {
                    set_error(err, input_line_no, "write error on subckt temp file");
                    goto fail;
                }

                state = ST_INSIDE_SUBCKT;
            } else {
                if (fputs(line, main_tmp) == EOF) {
                    set_error(err, input_line_no, "write error on main temp file");
                    goto fail;
                }

                state = ST_OUTSIDE;
            }
            break;

        default:
            set_error(err, input_line_no, "internal state error");
            goto fail;
        }
    }

    if (ferror(in)) {
        set_error(err, input_line_no, "read error on input file");
        goto fail;
    }

    if (state == ST_INSIDE_SUBCKT) {
        set_error(err, input_line_no, "unterminated .SUBCKT block");
        goto fail;
    }

    if (state == ST_OUTSIDE) {
        if (write_pending(main_tmp, &pending) != 0) {
            set_error(err, input_line_no, "write error on main temp file");
            goto fail;
        }
    } else {
        clear_pending(&pending);
    }

    close_if_open(&in);
    close_if_open(&main_tmp);
    close_if_open(&sub_tmp);

    main_tmp_read = fopen(main_tmp_path, "r");
    if (!main_tmp_read) {
        set_error(err, 0, "cannot reopen main temp file");
        goto fail;
    }

    main_out = fopen(opt->main_out_path, "w");
    if (!main_out) {
        set_error(err, 0, "cannot open final main output file");
        goto fail;
    }

    if (copy_stream(main_tmp_read, main_out) != 0) {
        set_error(err, 0, "error while copying main temp to final output");
        goto fail;
    }

    close_if_open(&main_tmp_read);
    close_if_open(&main_out);

    sub_tmp = fopen(sub_tmp_path, "r");
    if (!sub_tmp) {
        set_error(err, 0, "cannot reopen subckt temp file");
        goto fail;
    }

    sub_out = fopen(opt->subckt_out_path, "w");
    if (!sub_out) {
        set_error(err, 0, "cannot open final subckt output file");
        goto fail;
    }

    if (copy_stream(sub_tmp, sub_out) != 0) {
        set_error(err, 0, "error while copying subckt temp to final output");
        goto fail;
    }

    close_if_open(&sub_tmp);
    close_if_open(&sub_out);

    cleanup_file(main_tmp_path);
    cleanup_file(sub_tmp_path);
    return 0;

fail:
    close_if_open(&in);
    close_if_open(&main_tmp);
    close_if_open(&sub_tmp);
    close_if_open(&main_tmp_read);
    close_if_open(&main_out);
    close_if_open(&sub_out);

    cleanup_file(main_tmp_path);
    cleanup_file(sub_tmp_path);
    return -1;
}

/* ---------- CLI ---------- */

static void print_usage(const char *prog) {
    fprintf(stderr,
            "Usage:\n"
            "  %s <input.spi> <main_out.spi> <subckts.inc> <include_name>\n\n"
            "Example:\n"
            "  %s design.spi design_main.spi design_subckts.inc design_subckts.inc\n",
            prog, prog);
}

int main(int argc, char **argv) {
    ExtractOptions opt;
    ExtractError err;

    err.input_line_no = 0;
    err.message[0] = '\0';

    if (argc != 5) {
        print_usage(argv[0]);
        return 1;
    }

    opt.input_path = argv[1];
    opt.main_out_path = argv[2];
    opt.subckt_out_path = argv[3];
    opt.include_name = argv[4];

    if (extract_subckts_strict(&opt, &err) != 0) {
        if (err.input_line_no > 0) {
            fprintf(stderr, "Error at input line %ld: %s\n", err.input_line_no, err.message);
        } else if (err.message[0] != '\0') {
            fprintf(stderr, "Error: %s\n", err.message);
        } else {
            fprintf(stderr, "Error: unknown failure\n");
        }
        return 1;
    }

    return 0;
}
