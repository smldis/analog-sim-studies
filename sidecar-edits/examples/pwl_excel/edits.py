from pathlib import Path

from sidecar_edits import edits, pwl


BASE_DIR = "base"

waveforms = pwl.waveforms_from_file(
    Path(__file__).parent / "waveforms" / "startup.xlsx",
    sheet="startup",
)

pwl_source_lines = "\n".join(
    f"V{name} {name} 0 {waveform.render_pwl()}"
    for name, waveform in waveforms.items()
) + "\n"

EDITS = [
    edits.write_file(
        path="generated/pwl_sources.inc",
        content=pwl_source_lines,
        description="generate PWL sources from spreadsheet",
    ),
    edits.append_to_file(
        path="input.scs",
        content='include "generated/pwl_sources.inc"\n',
        description="include generated PWL sources",
    ),
]
