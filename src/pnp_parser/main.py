import typer
import json
from pathlib import Path
from pipeline_manager.specification_builder import SpecificationBuilder
from .fru_model import FRU
from .fru_model import SOC as BaseSoc

SPECIFICATION_VERSION = "20240723.13"
ASSETS_DIRECTORY = Path("./assets")

specification_builder = SpecificationBuilder(
    spec_version=SPECIFICATION_VERSION, assets_dir=ASSETS_DIRECTORY, check_urls=False
)

app = typer.Typer()


class Soc(BaseSoc):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/SoCs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )


@app.command()
def main(fru_json: str, output_spec: str) -> None:
    with open(fru_json) as f:
        hpm_data = json.load(f)
    fru = FRU.model_validate(hpm_data)

    soc = fru.HPM.Connectors.SOCs[0]
    soc_data = fru.HPM.Connectors.SOCs[0].model_dump()

    soc = Soc(**soc_data)
    soc.to_spec_node(specification_builder)

    specification = specification_builder.create_and_validate_spec(dump_spec="dump.json")
    print(specification)


if __name__ == "__main__":
    app()
