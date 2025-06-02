# OCP DC-MHS PnP parser

Copyright (c) 2025 [Antmicro](https://www.antmicro.com)

DC-MHS PnP parser is as script for converting Open Compute Project MHS (Modular Hardware System) PnP (Plug-and-Play) FRU (Field Replaceable Unit) into specification and dataflow compatible with [Pipeline Manager](https://github.com/antmicro/kenning-pipeline-manager) - data-based, application-agnostic web application for creating, visualizing and managing dataflows in various applications.

To learn more about OCP HMS project go to [OCP Server/MHS](https://www.opencompute.org/wiki/Server/DC-MHS) subproject page. Detailed specification and example FRU jsons can be found in [MHS workstream WIKI](https://www.opencompute.org/w/index.php?title=Server/MHS/DC-MHS-Specs-and-Designs).

## Installation

The application has a list of requirements in the `pyproject.toml` file.
Requirements and application can be installed using `pip`:

```bash
pip install .
```
