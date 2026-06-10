# Overview

This is an Asterfire-compliant Kit template. It demonstrates how to receive platform inputs, validate files, execute the core workflow, and generate user-facing outputs, a professional `report.md`, and a separate log file in the current working directory.

# Features

- Read platform form parameters from `kwargs['args']`.
- Validate input files and required parameters.
- Generate primary result files in the current working directory.
- Declare platform outputs with `@tool_io(outputs={...})` and keep them consistent with the returned dictionary.
- Generate a user-friendly `report.md` with run overview, method description, key results, visualizations, result interpretation, viewing instructions, and follow-up suggestions.
- Render `.pdb`, `.cif/.mmcif`, and `.sdf` structure outputs through `molstar` blocks when present.
- Embed generated images in the report; when only data files are available but visualization is useful, generate plots with matplotlib first.
- Save detailed execution logs to `run.log` instead of expanding them inside `report.md`.
- Provide a `demos/` directory for one-click example runs in the frontend.

# Inputs

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| input_file | file | Yes | Input file to process. A real Kit should restrict allowed extensions and clearly describe the expected file content. |

# Outputs

| Output | Description |
| --- | --- |
| output_file | Primary result file. In this template it is a text file; real Kits should replace it with the actual output such as CSV, JSON, structure files, model results, or archives. |
| report.md | User-facing report that directly presents key results, structure rendering, image visualizations, result interpretation, and follow-up suggestions. |
| run.log | Detailed execution log for troubleshooting. It is not expanded inside `report.md`. |
| success | Boolean flag indicating whether the primary output and report were generated successfully. |

# Notes

- Keep `input.json` minimal and expose only required inputs plus truly useful optional parameters.
- `SIF` must be a real runtime image, not a placeholder.
- Every Kit modification must update `config/configure.json` version and produce a new packaged zip.
- `config/configure.json` description should be user-friendly and must not exceed 400 characters.
- Structure outputs must be rendered with `molstar`; images or visualization-worthy data should be shown in the report with explanatory captions.
- After changing `input.json`, update `demos/demos.json` accordingly.

# References

1. Asterfire Platform Kit Development Guidelines.
2. Mol* / Molstar molecular visualization framework documentation.
