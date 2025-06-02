import typer
import json
from pathlib import Path
from pipeline_manager.specification_builder import SpecificationBuilder

SPECIFICATION_VERSION = '20240723.13'
ASSETS_DIRECTORY = Path("./assets")

specification_builder = SpecificationBuilder(
    spec_version=SPECIFICATION_VERSION,
    assets_dir=ASSETS_DIRECTORY,
    check_urls=True
)

app = typer.Typer()

@app.command()
def main(fru_json: str, output_spec: str):
    with open(fru_json) as f:
        hpm_data = json.load(f)
    for node in hpm_data["HPM"]:
        print(node)

if __name__ == "__main__":
    app()
