# Overview

This Asterfire Kit is adapted from a regular Python or command-line project. It receives inputs from the platform form, runs the original project logic inside the selected SIF runtime, and generates primary outputs, a professional `report.md`, and a separate execution log in the current working directory.

# Features

- Wrap an existing function entry point or command-line workflow into `class runner(Tool)`.
- Read platform form parameters from `kwargs['args']` and validate required inputs.
- Prepare input, output, and temporary files in the current working directory.
- Execute the original project workflow and verify generated outputs.
- Return platform-recognized output ports while keeping `@tool_io(outputs)` consistent with the returned dictionary.
- Generate a user-friendly `report.md` with run overview, method description, key results, structure/image visualizations, result viewing instructions, and follow-up suggestions.
- Render `.pdb`, `.cif/.mmcif`, and `.sdf` outputs with `molstar` blocks when present.
- Embed generated images in the report; when data files need visualization, generate plots with matplotlib first.
- Save detailed command output and errors to `run.log` instead of expanding them inside the report.
- Provide a `demos/` directory for one-click example runs in the frontend.

# Inputs

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| input_file | file | Yes | Example input file. Replace it with the actual inputs required by the original project and describe the expected format, fields, or structural requirements. |

# Outputs

| Output | Description |
| --- | --- |
| result_file | Primary result file. Replace it with the original project's real output, such as CSV, JSON, structure files, images, or archives. |
| report.md | User-facing report that directly presents key results, structure rendering, image visualizations, interpretation, and follow-up suggestions. |
| run.log | Detailed execution log for command output, errors, and exceptions. It is not expanded inside `report.md`. |
| success | Boolean flag indicating whether the primary output and report were generated successfully. |

# Notes

- The Kit `SIF` must come from the user or the SIF registry; placeholders are not allowed.
- Keep `input.json` minimal and expose only user-facing inputs or useful optional parameters.
- Every Kit modification must update `config/configure.json` version and produce a new packaged zip.
- `config/configure.json` description should explain the capability, input, and output, and must not exceed 400 characters.
- Structure and image outputs must be directly shown in `report.md`; visualization-worthy data should be plotted with matplotlib.
- After changing `input.json`, update `demos/demos.json` accordingly.

# References

1. Asterfire Platform Kit Development Guidelines.
2. Mol* / Molstar molecular visualization framework documentation.
