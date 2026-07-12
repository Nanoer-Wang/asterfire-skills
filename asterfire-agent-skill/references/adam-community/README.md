# adam-community PyPI README Reference

Snapshot date: 2026-06-30

Source page: https://pypi.org/project/adam-community/

Refresh source: https://pypi.org/pypi/adam-community/json

This file is a skill-local reference snapshot of the PyPI README sections that matter for ATP Agent Toolbox development. It is not a rule source; use the sibling `SKILL.md` as the active development checklist.

## Refresh Procedure

Use the PyPI JSON description as the README source:

```bash
curl -fsSL https://pypi.org/pypi/adam-community/json \
  | /home/pku-jianghong/liuzhaoqing/.conda/envs/abacus-env/bin/python -c \
    "import json, sys; data=json.load(sys.stdin); print(data['info']['version']); print(data['info'].get('description',''))"
```

After refreshing this snapshot, update the snapshot date above and rerun:

```bash
python3 scripts/check_docs_governance.py
```

## Snapshot Version

PyPI package version observed on 2026-06-30: `adam-community==1.2.5`.

## CLI Parse And Build

The README documents these development commands:

```bash
adam-cli parse .
adam-cli build .
```

The Python API exposes:

```python
from adam_community.cli.parser import parse_directory, parse_python_file
from adam_community.cli.build import build_package
```

ABACUS implication: Tool changes that affect parser-visible metadata should be verified with `parse_python_file(Path("changed_tool.py"))` or the project build checks.

## States Management

The README documents `setState`, `getState`, and `trackPath` from `adam_community.util`.

Important behavior for ABACUS tools:

- `setState("files", [...])` records files and merges with server/tool file state.
- `getState("files")` reads the merged file list.
- `trackPath(path)` records a file or directory and detects `is_dir` and `mtime`.
- The file list is FIFO-limited by the framework.

ABACUS implication: path browsing and compatibility state should go through `utils.path_states.register_path(...)`, which wraps Adam file state. This is separate from DAG structured outputs.

## Tool I/O Type System

The README describes Tool I/O as the type system for DAG workflow data passing. It uses:

```python
from adam_community.tool_types import tool_io, FileType
```

Predefined aliases such as `PDBFile`, `SDFFile`, `CSVFile`, `MDFile`, and scalar types such as `int`, `float`, `str`, `bool` can be used in `@tool_io(outputs={...})`.

ABACUS currently uses an ABACUS-wide alias:

```python
from typing import Annotated
from adam_community.tool_types import FileType

ABACUSPath = Annotated[str, FileType("*", "ABACUS workflow file or directory path")]
```

## `@tool_io` Output Declarations

The README recommends declaring output ports with descriptions:

```python
@tool_io(
    outputs={
        "report": (MDFile, "human-readable analysis report"),
        "best_score": (float, "best confidence score in the range 0-1"),
    },
)
class MyTool(Tool, calltype="python"):
    ...
```

Rules relevant to ATP Tool development:

- `outputs` is a dict keyed by port name.
- Values may be `Type` or `(Type, "description")`.
- FileType aliases declare file outputs.
- Scalar Python types declare parameter outputs.
- Port descriptions help the DAG Planner decide how to connect tools.

## Python Kit Structured Return

For Kit-style Python tools, the README says `call()` returns a flat dict:

```python
@tool_io(
    outputs={
        "predictions": (CSVFile, "prediction table"),
        "report": (MDFile, "analysis report"),
        "num_predictions": (int, "number of predictions"),
    },
)
class MyKit(Tool, calltype="python"):
    def call(self, kwargs):
        return {
            "predictions": "./results.csv",
            "report": "./report.md",
            "num_predictions": 42,
        }
```

Contract:

- Return a flat dict.
- Return keys must exactly match the `@tool_io(outputs={...})` keys.
- File paths should be relative to the working directory.
- The framework uses the `@tool_io` declaration to separate file outputs from scalar params and writes structured outputs.

ABACUS implication: `kwargs["tool_data"]` is not the DAG structured-output channel. It may still support current-result `outputShow()` or `summary()` compatibility, but declared workflow outputs must be returned by `call()`.

## Bash Toolbox `declare_outputs`

For bash-style tools, the README uses `self.declare_outputs(...)`:

```python
@tool_io(
    outputs={
        "docked": (SDFFile, "docking poses"),
        "log": (TXTFile, "runtime log"),
        "best_affinity": (float, "best binding free energy"),
    },
)
class DockingTool(Tool):
    def call(self, kwargs):
        self.declare_outputs({
            "docked": "result.sdf",
            "log": "docking.log",
            "best_affinity": -8.5,
        })
        return "run_docking ..."
```

Contract:

- `call()` returns the bash script.
- `self.declare_outputs(flat_dict)` writes structured outputs.
- Keys must match the `@tool_io(outputs={...})` declaration.

## Contract Extraction

The README documents:

```python
from adam_community.tool_types import get_tool_contract

contract = get_tool_contract(DockingTool)
```

The extracted contract separates file outputs from scalar output params. The parser also emits `function.io_contract` for statically parsed tools.

ABACUS implication: parser/build tests should check `io_contract.outputs` and, when scalar outputs are used, `output_params`.
