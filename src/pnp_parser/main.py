import typer
import json
from pathlib import Path
from pipeline_manager.specification_builder import SpecificationBuilder
from .fru_model import FRU

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
    fru = FRU.model_validate(hpm_data)
    print(fru.HPM.BoardInfo.Manufacturer)

if __name__ == "__main__":
    app()
