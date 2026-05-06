from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Literal, Protocol, TypeAlias


class RenderContext(Protocol):
    target_dir: Path
    editfile_dir: Path
    editfile_path: Path
    params: dict[str, object]


@dataclass(frozen=True)
class SourceFrame:
    path: Path
    line: int
    function: str

    def format(self, editfile_path: Path | None = None) -> str:
        display_path = self.path
        if editfile_path is not None:
            editfile_dir = editfile_path.parent.resolve()
            try:
                display_path = self.path.resolve().relative_to(editfile_dir)
            except ValueError:
                display_path = self.path
        return f"{display_path}:{self.line} in {self.function}"


@dataclass(frozen=True)
class ExtractSubcktsEdit:
    op: Literal["extract_subckts"]
    input: str
    output_main: str
    output_subckts: str
    include: str | None
    description: str | None
    optional: bool
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        output_subckts = render.format_path_text(self.output_subckts, context.params)
        include = render.format_path_text(self.include or output_subckts, context.params)
        render.run_extract_subckts(
            context.target_dir,
            render.format_path_text(self.input, context.params),
            render.format_path_text(self.output_main, context.params),
            output_subckts,
            include,
            self.optional,
            edit_description(self),
        )


@dataclass(frozen=True)
class CopyFileEdit:
    op: Literal["copy_file"]
    path: str
    to: str | None
    description: str | None
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        source = render.resolve_editfile_path(context.editfile_dir, self.path, context.params)
        dest_name = render.format_path_text(self.to or source.name, context.params)
        render.apply_copy_file(context.target_dir, source, dest_name, edit_description(self))


@dataclass(frozen=True)
class WriteFileEdit:
    op: Literal["write_file"]
    path: str
    content: str
    description: str | None
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        path = render.format_path_text(self.path, context.params)
        content = render.format_text(self.content, context.params)
        render.apply_write_file(context.target_dir, path, content)


@dataclass(frozen=True)
class AppendToFileEdit:
    op: Literal["append_to_file"]
    path: str
    content: str
    description: str | None
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        path = render.format_path_text(self.path, context.params)
        content = render.format_text(self.content, context.params)
        render.apply_append_to_file(context.target_dir, path, content, edit_description(self))


@dataclass(frozen=True)
class InsertSeriesSourceAtInstanceNetEdit:
    op: Literal["insert_series_source_at_instance_net"]
    path: str
    instance: str
    net: str
    internal_net: str
    source_line: str
    description: str | None
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        target = context.target_dir / render.format_path_text(self.path, context.params)
        source_params = context.params | {
            "net": self.net,
            "internal_net": self.internal_net,
        }
        render.apply_insert_series_source_at_instance_net(
            target,
            self.instance,
            self.net,
            self.internal_net,
            render.format_text(self.source_line, source_params),
            edit_description(self),
        )


@dataclass(frozen=True)
class ReplaceEdit:
    op: Literal["replace"]
    path: str
    old: str
    new: str
    description: str | None
    allow_no_match: bool
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        target = context.target_dir / render.format_path_text(self.path, context.params)
        render.apply_replace_text(
            target,
            render.format_text(self.old, context.params),
            render.format_text(self.new, context.params),
            self.allow_no_match,
            edit_description(self),
        )


@dataclass(frozen=True)
class RegexReplaceEdit:
    op: Literal["regex_replace"]
    path: str
    pattern: str
    new: str
    count: int
    description: str | None
    allow_no_match: bool
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        target = context.target_dir / render.format_path_text(self.path, context.params)
        render.apply_regex_replace_text(
            target,
            self.pattern,
            render.format_text(self.new, context.params),
            self.count,
            self.allow_no_match,
            edit_description(self),
        )


@dataclass(frozen=True)
class RunEdit:
    op: Literal["run"]
    command: list[str]
    description: str | None
    optional: bool
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        command = [render.format_path_text(str(arg), context.params) for arg in self.command]
        render.run_command_args(context.target_dir, command, self.optional, edit_description(self))


@dataclass(frozen=True)
class PatchEdit:
    op: Literal["patch"]
    patch: str
    strip: int
    description: str | None
    optional: bool
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        patch_text = render.format_text(self.patch, context.params)
        render.run_external_patch(
            context.target_dir,
            patch_text,
            ["patch", f"-p{self.strip}"],
            self.optional,
            edit_description(self),
        )


@dataclass(frozen=True)
class ApplyPatchEdit:
    op: Literal["apply_patch"]
    patch: str
    binary: str | None
    command: list[str] | None
    description: str | None
    optional: bool
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        command = None
        if self.command is not None:
            command = [render.format_path_text(str(arg), context.params) for arg in self.command]
        render.apply_patch_text(
            context.target_dir,
            render.format_text(self.patch, context.params),
            render.format_path_text(self.binary, context.params) if self.binary is not None else None,
            command,
            self.optional,
            edit_description(self),
        )


EditSpec: TypeAlias = (
    ExtractSubcktsEdit
    | CopyFileEdit
    | WriteFileEdit
    | AppendToFileEdit
    | InsertSeriesSourceAtInstanceNetEdit
    | ReplaceEdit
    | RegexReplaceEdit
    | RunEdit
    | PatchEdit
    | ApplyPatchEdit
)


def extract_subckts(
    *,
    input: str,
    output_main: str,
    output_subckts: str,
    include: str | None = None,
    description: str | None = None,
    optional: bool = False,
) -> ExtractSubcktsEdit:
    """Extract subcircuit definitions from a netlist into a side include file.

    The renderer runs the packaged ``extract_subckts`` helper in the rendered
    run directory. ``input`` is read, ``output_main`` receives the main netlist
    with subckt bodies removed, and ``output_subckts`` receives the extracted
    subckt definitions. If ``include`` is omitted, it defaults to
    ``output_subckts``.

    Path fields are formatted with render parameters and environment variables.
    Set ``optional=True`` only when it is acceptable to skip extraction if the
    helper cannot run.

    Example::

        edits.extract_subckts(
            input="input.scs",
            output_main="input_main.scs",
            output_subckts="subckts.inc",
        )
    """
    return ExtractSubcktsEdit(
        op="extract_subckts",
        input=input,
        output_main=output_main,
        output_subckts=output_subckts,
        include=include,
        description=description,
        optional=optional,
        source_stack=_capture_source_stack(),
    )


def copy_file(
    *,
    path: str,
    to: str | None = None,
    description: str | None = None,
) -> CopyFileEdit:
    """Copy a file from the edit file directory into the rendered run directory.

    ``path`` is resolved relative to the directory containing the edit file unless
    it is absolute. ``to`` is the destination path inside the rendered run
    directory; if omitted, the copied file keeps its source filename.

    Source and destination paths are formatted with render parameters and
    environment variables. The edit fails if the source file does not exist.

    Example::

        edits.copy_file(
            path="assets/model_override.scs",
            to="include/model_override.scs",
        )
    """
    return CopyFileEdit(
        op="copy_file",
        path=path,
        to=to,
        description=description,
        source_stack=_capture_source_stack(),
    )


def write_file(
    *,
    path: str,
    content: str,
    description: str | None = None,
) -> WriteFileEdit:
    """Write generated text to a file in the rendered run directory.

    The destination ``path`` is inside the rendered run directory. Parent
    directories are created automatically, and existing files are overwritten.

    ``path`` is formatted with render parameters and environment variables.
    ``content`` is formatted with render parameters but does not expand
    environment variables.

    Example::

        edits.write_file(
            path="generated/pwl_sources.inc",
            content="Vstim in 0 PWL(0 0 1n {vdd})\\n",
        )
    """
    return WriteFileEdit(
        op="write_file",
        path=path,
        content=content,
        description=description,
        source_stack=_capture_source_stack(),
    )


def append_to_file(
    *,
    path: str,
    content: str,
    description: str | None = None,
) -> AppendToFileEdit:
    """Append generated text to an existing file in the rendered run directory.

    The target ``path`` must already exist in the rendered run directory. The
    renderer appends exactly ``content``; it does not add a newline for you.

    ``path`` is formatted with render parameters and environment variables.
    ``content`` is formatted with render parameters but does not expand
    environment variables.

    Example::

        edits.append_to_file(
            path="input_main.scs",
            content='include "generated/pwl_sources.inc"\\n',
        )
    """
    return AppendToFileEdit(
        op="append_to_file",
        path=path,
        content=content,
        description=description,
        source_stack=_capture_source_stack(),
    )


def insert_series_source_at_instance_net(
    *,
    path: str,
    instance: str,
    net: str,
    internal_net: str,
    source_line: str,
    description: str | None = None,
) -> InsertSeriesSourceAtInstanceNetEdit:
    """Insert a source in series with one net on a uniquely named X instance.

    The renderer finds exactly one matching logical instance statement in the
    rendered file, inserts ``source_line`` before it, and replaces one occurrence
    of ``net`` in that instance text with ``internal_net``. Continuation lines
    are kept with the selected instance text.

    ``source_line`` is formatted with normal render parameters plus ``net`` and
    ``internal_net``. The first version rejects commented instance statements
    containing ``$``, ``;``, or ``*``. It also fails if the instance is missing
    or ambiguous, or if the selected net is missing or repeated on that instance.

    Instance names must start with ``X``. For netlists that duplicate the second
    character in instance names, a request for ``XFOO`` may also match
    ``XFFOO``. If both forms are present, the edit fails as ambiguous.

    Example::

        edits.insert_series_source_at_instance_net(
            path="input.scs",
            instance="X_SIDE_INJECT_001",
            net="in",
            internal_net="in__sidecar_inj",
            source_line=(
                "Vinj {net} {internal_net} "
                "PULSE(0 1.2 0 10p 10p 4n 8n)"
            ),
        )
    """
    if not instance.lower().startswith("x"):
        raise ValueError("instance must start with X")
    return InsertSeriesSourceAtInstanceNetEdit(
        op="insert_series_source_at_instance_net",
        path=path,
        instance=instance,
        net=net,
        internal_net=internal_net,
        source_line=source_line,
        description=description,
        source_stack=_capture_source_stack(),
    )


def replace(
    *,
    path: str,
    old: str,
    new: str,
    description: str | None = None,
    allow_no_match: bool = False,
) -> ReplaceEdit:
    """Replace all occurrences of literal text in a rendered file.

    ``path`` is inside the rendered run directory. ``old`` and ``new`` are
    formatted with render parameters before replacement. Environment variables
    are expanded in ``path`` only, not in replacement text.

    The edit fails if ``old`` is not found. Set ``allow_no_match=True`` when an
    absent target is acceptable.

    Example::

        edits.replace(
            path="input.scs",
            old="parameters corner=seed",
            new="parameters corner={corner}",
        )
    """
    return ReplaceEdit(
        op="replace",
        path=path,
        old=old,
        new=new,
        description=description,
        allow_no_match=allow_no_match,
        source_stack=_capture_source_stack(),
    )


def regex_replace(
    *,
    path: str,
    pattern: str,
    new: str,
    count: int = 0,
    description: str | None = None,
    allow_no_match: bool = False,
) -> RegexReplaceEdit:
    """Replace text in a rendered file using a regular expression.

    ``pattern`` is passed to Python ``re.subn`` with ``re.MULTILINE``. ``new`` is
    formatted with render parameters before replacement. ``count=0`` means
    replace all matches.

    The edit fails if the pattern does not match. Set ``allow_no_match=True``
    when an absent match is acceptable.

    Example::

        edits.regex_replace(
            path="input.scs",
            pattern=r"^parameters .*",
            new="parameters vdd={vdd}",
        )
    """
    return RegexReplaceEdit(
        op="regex_replace",
        path=path,
        pattern=pattern,
        new=new,
        count=count,
        description=description,
        allow_no_match=allow_no_match,
        source_stack=_capture_source_stack(),
    )


def run(
    *,
    command: list[str],
    description: str | None = None,
    optional: bool = False,
) -> RunEdit:
    """Run an external command in the rendered run directory.

    Each command argument is converted to text, formatted with render
    parameters, and expanded for environment variables. The command runs with
    the rendered run directory as the current working directory.

    Set ``optional=True`` only when it is acceptable to skip the command if it is
    missing or exits unsuccessfully.

    Example::

        edits.run(
            command=["./run_sim.sh", "{corner}"],
            description="run simulator setup script",
        )
    """
    return RunEdit(
        op="run",
        command=command,
        description=description,
        optional=optional,
        source_stack=_capture_source_stack(),
    )


def patch(
    *,
    patch: str,
    strip: int = 0,
    description: str | None = None,
    optional: bool = False,
) -> PatchEdit:
    """Apply a unified diff with the system patch command.

    ``patch`` is formatted with render parameters and sent to ``patch -p{strip}``
    in the rendered run directory. Use this for normal unified diffs when the
    system ``patch`` command is available.

    Set ``optional=True`` only when it is acceptable to skip the patch if the
    command is missing or the patch fails.

    Example::

        edits.patch(
            patch="*** unified diff text ***",
            strip=0,
        )
    """
    return PatchEdit(
        op="patch",
        patch=patch,
        strip=strip,
        description=description,
        optional=optional,
        source_stack=_capture_source_stack(),
    )


def apply_patch(
    *,
    patch: str,
    binary: str = "apply_patch",
    command: list[str] | None = None,
    description: str | None = None,
    optional: bool = False,
) -> ApplyPatchEdit:
    """Apply an apply_patch patch in the rendered run directory.

    ``patch`` is formatted with render parameters and sent to the configured
    ``apply_patch`` command in the rendered run directory. By default the
    renderer looks for an ``apply_patch`` executable on ``PATH``. Pass
    ``binary=...`` to choose another executable, or ``command=[...]`` to provide
    the full command.

    Set ``optional=True`` only when it is acceptable to skip the patch if the
    command is missing or the patch fails.

    Example::

        edits.apply_patch(
            patch="*** Begin Patch\\n*** Add File: note.txt\\n+hello\\n*** End Patch\\n",
        )
    """
    return ApplyPatchEdit(
        op="apply_patch",
        patch=patch,
        binary=binary if command is None else None,
        command=command,
        description=description,
        optional=optional,
        source_stack=_capture_source_stack(),
    )


def is_edit_spec(value: object) -> bool:
    return isinstance(
        value,
        (
            ExtractSubcktsEdit,
            CopyFileEdit,
            WriteFileEdit,
            AppendToFileEdit,
            InsertSeriesSourceAtInstanceNetEdit,
            ReplaceEdit,
            RegexReplaceEdit,
            RunEdit,
            PatchEdit,
            ApplyPatchEdit,
        ),
    )


def edit_description(edit: EditSpec) -> str:
    if edit.description:
        return edit.description
    return f"{edit.op} edit"


def _capture_source_stack(limit: int = 4) -> tuple[SourceFrame, ...]:
    frames = []
    frame = inspect.currentframe()
    if frame is not None:
        frame = frame.f_back

    while frame is not None and len(frames) < limit:
        if _is_user_frame(frame):
            info = inspect.getframeinfo(frame, context=0)
            frames.append(
                SourceFrame(
                    path=Path(info.filename).resolve(),
                    line=info.lineno,
                    function=info.function,
                )
            )
        frame = frame.f_back

    return tuple(frames)


def _is_user_frame(frame: FrameType) -> bool:
    return Path(frame.f_code.co_filename).resolve() != Path(__file__).resolve()
