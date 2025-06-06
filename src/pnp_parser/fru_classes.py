from .fru_model import MemorySubsystem as MemorySubsystemBase
from .fru_model import Composite as CompositeBase
from .fru_model import Mxio as MxioBase
from .fru_model import Mpic as MpicBase
from .fru_model import PowerSupply as PowerSupplyBase
from .fru_model import OCPMezzanineSlot as OCPMezzanineSlotBase
from .fru_model import ControlPanel as ControlPanelBase
from .fru_model import SoC as SocBase
from .fru_model import Sci as SciBase
from .fru_model import Fan as FanBase
from .fru_model import RealTimeClockBattery
from .fru_model import PowerDistributionBoard
from pipeline_manager.specification_builder import SpecificationBuilder

SPECIFICATION_VERSION = "20240723.13"
specification_builder = SpecificationBuilder(spec_version=SPECIFICATION_VERSION)


class Soc(SocBase):
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
        node_name = f"Rev-{self.Revision}-ver-{self.Version}"
        builder.add_node_type(
            name=node_name,
            category="Connectors/SCIs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(name=node_name, interfacename=bus.Type, interfacetype=bus.Type.lower())
        builder.add_node_type_property(name=node_name, propname="Revision", proptype="constant", default=self.Revision)
        builder.add_node_type_property(name=node_name, propname="Version", proptype="constant", default=self.Version)
        builder.add_node_type_property(
            name=node_name, propname="CommonCircuitType", proptype="constant", default=self.CommonCircuitType
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


class PDB(PowerDistributionBoard):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Power Distribution Boards",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
        builder.add_node_type_property(name=self.Identifier, propname="Type", proptype="constant", default=self.Type)
        builder.add_node_type_property(
            name=self.Identifier, propname="ConnectorType", proptype="constant", default=self.ConnectorType
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
            category="Connectors/MPICs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )


class Mpic(MpicBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/MXIOs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )


class RtcBattery(RealTimeClockBattery):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/RTC Batteries",
        )


class PowerSupply(PowerSupplyBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Power Supplies",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )


class OCPMezzanineSlot(OCPMezzanineSlotBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/OCPMezzanineSlots",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )


class ControlPanel(ControlPanelBase):
    def to_spec_node(self, builder: SpecificationBuilder = specification_builder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/ControlPanels",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
