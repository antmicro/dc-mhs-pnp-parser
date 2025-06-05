import typer
import json
from pathlib import Path
from pipeline_manager.specification_builder import SpecificationBuilder
from .fru_model import FRU, MemorySubsystem
from .fru_model import SOC as BaseSoc

SPECIFICATION_VERSION = "20240723.13"

specification_builder = SpecificationBuilder(spec_version=SPECIFICATION_VERSION)

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


class MemSubsystem(MemorySubsystem):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        for slot in self.Slots:
            builder.add_node_type(
                name=slot.Identifier,
                category="Connectors/MemorySubsystems/Slots",
            )
            for bus in slot.ConnectedBuses:
                builder.add_node_type_interface(
                    name=slot.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
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

    mem_subsystem = fru.HPM.Connectors.MemorySubsystems[0]
    mem_subsystem_data = fru.HPM.Connectors.MemorySubsystems[0].model_dump()
    mem_subsystem = MemSubsystem(**mem_subsystem_data)
    mem_subsystem.to_spec_node(specification_builder)

    specification_builder.metadata_add_param(paramname="connectionStyle", paramvalue="orthogonal")
    specification_builder.metadata_add_param(paramname="twoColumn", paramvalue=True)

    specification = specification_builder.create_and_validate_spec(dump_spec="dump.json", sort_spec=True)
    with open(output_spec, "w") as f:
        json.dumps(specification, sort_keys=True, indent=4)


if __name__ == "__main__":
    app()
