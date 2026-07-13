"""Generate or check the functional-decomposition dependency table."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from netlist_decomposition.dependencies import (  # noqa: E402
    default_output_path,
    render_dependency_table,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output_path(),
        help="generated Markdown path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when the generated file is stale",
    )
    args = parser.parse_args(argv)
    rendered = render_dependency_table()

    if args.check:
        try:
            current = args.output.read_text(encoding="utf-8")
        except FileNotFoundError:
            current = ""
        if current != rendered:
            print(f"stale generated dependency table: {args.output}", file=sys.stderr)
            return 1
        return 0

    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
