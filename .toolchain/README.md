# Toolchain

Project-local Python environment for diagnostics that the units themselves do
not depend on. Nothing here is installed into `$HOME`, and no shell rc file is
touched.

    python -m venv --system-site-packages .toolchain/venv
    .toolchain/venv/bin/pip install bokeh graphviz

`--system-site-packages` so `dask`/`distributed` are inherited rather than
duplicated: this environment adds diagnostics, it does not fork the runtime.

| package | what it unlocks |
| --- | --- |
| `bokeh` | the Dask dashboard, and `distributed.performance_report(...)` |
| `graphviz` | `ass.visualize.render(...)`; also needs a system `dot` |

Run anything that needs them with `.toolchain/venv/bin/python`. The test suite
and both example studies run on plain `python` and do not need this.
