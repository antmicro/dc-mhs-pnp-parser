# Fru2Graph

Copyright (c) 2025 [Antmicro](https://www.antmicro.com)

Fru2Graph is a tool for converting Open Compute Project DC-MHS (Data Center Modular Hardware System) PnP (Plug-and-Play) FRU (Field Replaceable Unit) JSON files into specification and dataflow files compatible with [Pipeline Manager](https://github.com/antmicro/kenning-pipeline-manager) - data-based, application-agnostic web application for creating, visualizing and managing dataflows in various applications.
This tool supports v0.5 FRU JSON files.

To learn more about the OCP MHS project visit [the OCP wiki's MHS subproject page](https://www.opencompute.org/wiki/Server/MHS).
The detailed specification and example FRU JSON files can be found in [the DC-MHS Specs and Designs wiki page](https://www.opencompute.org/w/index.php?title=Server/MHS/DC-MHS-Specs-and-Designs).

## Installation

The tool can be installed globally using `pipx`:

```bash
pipx install git+https://github.com/antmicro/fru2graph.git
```

Alternatively, the tool can be installed in a virtual environment using `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"    # editable install with dev packages
```

## Example usage

1. Download the M-PnP v0.5 Release Package .zip file ([DC-MHS-Specs-and-Designs#Specifications](https://www.opencompute.org/w/index.php?title=Server/MHS/DC-MHS-Specs-and-Designs#Specifications))

2. Extract the .zip file in your preferred location

3. Generate the specification and dataflow files:
    ```bash
    fru2graph "path/to/Release_0.5.0/JSON Files/Mockups/HPM/hpm-fru-mockup-type1-hpm-example-v0.6.8.json" spec.json dataflow.json
    ```

The resulting graph can be shown in two ways:

1. through Visual System Designer (VSD):
    * visit [https://designer.antmicro.com/vsd](https://designer.antmicro.com/vsd)
    * drag-and-drop or choose the specification and dataflow files

2. locally using Pipeline Manager (requires installing Fru2Graph in a virtual environment):
    ```bash
    source .venv/bin/activate
    # Generates a standalone `index.html` file
    pipeline_manager build static-html --single-html index.html spec.json dataflow.json --workspace-directory workspace
    ```
