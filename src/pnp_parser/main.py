import typer
import json
from pathlib import Path

from pipeline_manager.specification_builder import SpecificationBuilder
from pipeline_manager.frontend_builder import build_prepare
from .fru_model import FRU
from .fru_model import MemorySubsystem as MemorySubsystemBase
from .fru_model import Composite as CompositeBase
from .fru_model import Mxio as MxioBase
from .fru_model import Mpic as MpicBase
from .fru_model import PowerSupply as PowerSupplyBase
from .fru_model import SOC as BaseSoc
from .fru_model import SCI as SciBase
from .fru_model import Fan as FanBase
from .fru_model import RealTimeClockBattery

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


class Sci(SciBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name="DC-SCM 2.1",
            category="Connectors/SCIs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(name="DC-SCM 2.1", interfacename=bus.Type, interfacetype=bus.Type.lower())
        builder.add_node_type_property(
            name="DC-SCM 2.1", propname="Revision", proptype="constant", default=self.Revision
        )
        builder.add_node_type_property(name="DC-SCM 2.1", propname="Version", proptype="constant", default=self.Version)
        builder.add_node_type_property(
            name="DC-SCM 2.1", propname="CommonCircuitType", proptype="constant", default=self.CommonCircuitType
        )


class Fan(FanBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Fans",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
        builder.add_node_type_property(
            name=self.Identifier, propname="MaximumPower (W)", proptype="constant", default=f"{self.MaximumPowerWatts}"
        )
        builder.add_node_type_property(
            name=self.Identifier, propname="ConnectorType", proptype="constant", default=self.ConnectorType
        )
        builder.add_node_type_property(
            name=self.Identifier, propname="HotPlugSuported", proptype="constant", default=f"{self.HotPlugSupported}"
        )


class MemorySubsystem(MemorySubsystemBase):
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


class Composite(CompositeBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Composites",
        )
        builder.add_node_type_interface(name=self.Identifier, interfacename=self.Type, interfacetype=self.Type.lower())


class Mxio(MxioBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Mxios",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )


class Mpic(MpicBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Mpics",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
class RtcBattery(RealTimeClockBattery):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Mxios",
        )


class PowerSupply(PowerSupplyBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/PowerSupplies",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )


def add_node(fru: FRU, prop: str, class_name: type, specification_builder: SpecificationBuilder) -> None:
    node_data = getattr(fru.HPM.Connectors, prop)[0].model_dump()
    node = class_name(**node_data)
    node.to_spec_node(specification_builder)


@app.command()
def main(fru_json: str, output_spec: str) -> None:
    with open(fru_json) as f:
        hpm_data = json.load(f)
    fru = FRU.model_validate(hpm_data)

    add_node(fru, "SOCs", Soc, specification_builder)
    add_node(fru, "MemorySubsystems", MemorySubsystem, specification_builder)
    add_node(fru, "Composites", Composite, specification_builder)
    add_node(fru, "Mxios", Mxio, specification_builder)
    add_node(fru, "Mpics", Mpic, specification_builder)
    add_node(fru, "PowerSupplies", PowerSupply, specification_builder)
    add_node(fru, "SCIs", Sci, specification_builder)
    add_node(fru, "Fans", Fan, specification_builder)
    add_node(fru, "RealTimeClockBatteries", RtcBattery, specification_builder)

    specification_builder.metadata_add_param(paramname="connectionStyle", paramvalue="orthogonal")
    specification_builder.metadata_add_param(paramname="twoColumn", paramvalue=True)

    workspace = Path("workspace")
    if workspace.exists():
        build_prepare(workspace, skip_install_deps=True)
    else:
        build_prepare(workspace)
    specification = specification_builder.create_and_validate_spec(
        dump_spec="dump.json", sort_spec=True, workspacedir=str(workspace)
    )
    with open(output_spec, "w") as f:
        json.dump(specification, f, sort_keys=True, indent=4)


if __name__ == "__main__":
    app()
