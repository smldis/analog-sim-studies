#include <stdio.h>
#include <string.h>
#include <ctype.h>

#define MAX_LINE 8192
#define MAX_PENDING 3

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

static int append_pending(PendingBuffer *pb,
                          FILE *main_out,
                          const char *line,
                          long line_no,
                          ExtractError *err)
{
    if (pb->count >= MAX_PENDING) {
        if (fputs(pb->lines[0], main_out) == EOF) {
            set_error(err, line_no, "write error on main output file");
            return -1;
        }

        memmove(&pb->lines[0], &pb->lines[1], (MAX_PENDING - 1) * MAX_LINE);
        memmove(&pb->line_no[0], &pb->line_no[1], (MAX_PENDING - 1) * sizeof(pb->line_no[0]));
        pb->count--;
    }

    if (safe_copy_line(pb->lines[pb->count], sizeof(pb->lines[pb->count]), line) != 0) {
        set_error(err, line_no, "input line exceeds pending buffer capacity");
        return -1;
    }

    pb->line_no[pb->count] = line_no;
    pb->count++;
    return 0;
}

static int line_was_truncated(const char *line, FILE *in) {
    size_t n = strlen(line);
    if (n == 0) {
        return 0;
    }
    return (line[n - 1] != '\n' && !feof(in));
}

static void close_if_open(FILE **fp) {
    if (*fp) {
        fclose(*fp);
        *fp = NULL;
    }
}

/* ---------- main extraction ---------- */

int extract_subckts_strict(const ExtractOptions *opt, ExtractError *err) {
    FILE *in = NULL;
    FILE *main_tmp = NULL;
    FILE *sub_tmp = NULL;

    char line[MAX_LINE];

    long input_line_no = 0;
    int include_inserted = 0;
    State state = ST_OUTSIDE;
    PendingBuffer pending;

    pending.count = 0;

    if (!opt || !opt->input_path || !opt->main_out_path || !opt->subckt_out_path || !opt->include_name) {
        set_error(err, 0, "invalid arguments");
        return -1;
    }

    in = fopen(opt->input_path, "r");
    if (!in) {
        set_error(err, 0, "cannot open input file");
        return -1;
    }

    main_tmp = fopen(opt->main_out_path, "w");
    if (!main_tmp) {
        set_error(err, 0, "cannot open main output file");
        goto fail;
    }

    sub_tmp = fopen(opt->subckt_out_path, "w");
    if (!sub_tmp) {
        set_error(err, 0, "cannot open subckt output file");
        goto fail;
    }

    while (fgets(line, sizeof(line), in) != NULL) {
        input_line_no++;

        if (line_was_truncated(line, in)) {
            set_error(err, input_line_no, "input line exceeds MAX_LINE");
            goto fail;
        }

        switch (state) {
        case ST_OUTSIDE:
            if (is_blank_line(line) || starts_with_three_stars(line)) {
                if (append_pending(&pending, main_tmp, line, input_line_no, err) != 0) {
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
    return 0;

fail:
    close_if_open(&in);
    close_if_open(&main_tmp);
    close_if_open(&sub_tmp);
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
