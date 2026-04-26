from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Literal, Protocol, TypeAlias


class RenderContext(Protocol):
    target_dir: Path
    config_dir: Path
    config_path: Path
    params: dict[str, object]


@dataclass(frozen=True)
class SourceFrame:
    path: Path
    line: int
    function: str

    def format(self, config_path: Path | None = None) -> str:
        display_path = self.path
        if config_path is not None:
            config_dir = config_path.parent.resolve()
            try:
                display_path = self.path.resolve().relative_to(config_dir)
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

        source = render.resolve_config_path(context.config_dir, self.path, context.params)
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
class AppendFileEdit:
    op: Literal["append_file"]
    path: str
    content: str
    description: str | None
    source_stack: tuple[SourceFrame, ...]

    def apply(self, context: RenderContext) -> None:
        from sidecar_edits import render

        path = render.format_path_text(self.path, context.params)
        content = render.format_text(self.content, context.params)
        render.apply_append_file(context.target_dir, path, content, edit_description(self))


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
    | AppendFileEdit
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
    """Extract subcircuit definitions from a netlist into a side include file."""
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
    """Copy a file from the config directory into the rendered run directory."""
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
    """Write generated text to a file in the rendered run directory."""
    return WriteFileEdit(
        op="write_file",
        path=path,
        content=content,
        description=description,
        source_stack=_capture_source_stack(),
    )


def append_file(
    *,
    path: str,
    content: str,
    description: str | None = None,
) -> AppendFileEdit:
    """Append generated text to an existing file in the rendered run directory."""
    return AppendFileEdit(
        op="append_file",
        path=path,
        content=content,
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
    """Replace all occurrences of literal text in a rendered file."""
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
    """Replace text in a rendered file using a regular expression."""
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
    """Run an external command in the rendered run directory."""
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
    """Apply a unified diff with the system patch command."""
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
    """Apply an apply_patch patch in the rendered run directory."""
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
            AppendFileEdit,
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
