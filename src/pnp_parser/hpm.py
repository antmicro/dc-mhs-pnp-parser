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
from .fru_model import Connectors
from pipeline_manager.specification_builder import SpecificationBuilder
from typing import List


class Soc(SocBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/SoCs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
            buses.setdefault(bus.Identifier, []).append([self.Identifier, bus.Type])
        nodes.append(self.Identifier)


class Sci(SciBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        node_name = f"DC-SCM Rev.{self.Revision}"
        builder.add_node_type(
            name=node_name,
            category="Connectors/SCIs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=node_name, interfacename=bus.Type, interfacetype=bus.Type.lower(), side="right"
            )
            buses.setdefault(bus.Identifier, []).append(
                [
                    node_name,
                    bus.Type,
                ]
            )
        builder.add_node_type_property(name=node_name, propname="Revision", proptype="constant", default=self.Revision)
        builder.add_node_type_property(name=node_name, propname="Version", proptype="constant", default=self.Version)
        builder.add_node_type_property(
            name=node_name, propname="CommonCircuitType", proptype="constant", default=self.CommonCircuitType
        )
        nodes.append(node_name)


class Fan(FanBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Fans",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
            buses.setdefault(bus.Identifier, []).append([self.Identifier, bus.Type])
        builder.add_node_type_property(
            name=self.Identifier, propname="MaximumPower (W)", proptype="constant", default=f"{self.MaximumPowerWatts}"
        )
        builder.add_node_type_property(
            name=self.Identifier, propname="ConnectorType", proptype="constant", default=self.ConnectorType
        )
        builder.add_node_type_property(
            name=self.Identifier, propname="HotPlugSuported", proptype="constant", default=f"{self.HotPlugSupported}"
        )
        nodes.append(self.Identifier)


class PDB(PowerDistributionBoard):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Power Distribution Boards",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
            buses.setdefault(bus.Identifier, []).append([self.Identifier, bus.Type])
        builder.add_node_type_property(name=self.Identifier, propname="Type", proptype="constant", default=self.Type)
        builder.add_node_type_property(
            name=self.Identifier, propname="ConnectorType", proptype="constant", default=self.ConnectorType
        )
        nodes.append(self.Identifier)


class MemorySubsystem(MemorySubsystemBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        for slot in self.Slots:
            builder.add_node_type(
                name=slot.Identifier,
                category="Connectors/MemorySubsystems/Slots",
            )
            for bus in slot.ConnectedBuses:
                builder.add_node_type_interface(
                    name=slot.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
                )
                buses.setdefault(bus.Identifier, []).append([slot.Identifier, bus.Type])
            builder.add_node_type_property(
                name=slot.Identifier, propname="Proximity", proptype="constant", default=slot.Proximity
            )
            nodes.append(slot.Identifier)


class Composite(CompositeBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Composites",
        )
        builder.add_node_type_interface(name=self.Identifier, interfacename=self.Type, interfacetype=self.Type.lower())
        builder.add_node_type_property(name=self.Identifier, propname="Type", proptype="constant", default=self.Type)
        nodes.append(self.Identifier)


class Mxio(MxioBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/MPICs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
            buses.setdefault(bus.Identifier, []).append([self.Identifier, bus.Type])
        builder.add_node_type_property(
            name=self.Identifier, propname="ConnectorType", proptype="constant", default=self.ConnectorType
        )
        nodes.append(self.Identifier)


class Mpic(MpicBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/MXIOs",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
            buses.setdefault(bus.Identifier, []).append([self.Identifier, bus.Type])
        builder.add_node_type_property(
            name=self.Identifier, propname="ConnectorType", proptype="constant", default=self.ConnectorType
        )
        builder.add_node_type_property(
            name=self.Identifier,
            propname="AdjustedMaximumActualPowerSupportedWatts",
            proptype="constant",
            default=str(self.AdjustedMaximumActualPowerSupportedWatts),
        )
        nodes.append(self.Identifier)


class RtcBattery(RealTimeClockBattery):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/RTC Batteries",
        )
        nodes.append(self.Identifier)


class PowerSupply(PowerSupplyBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/Power Supplies",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
            buses.setdefault(bus.Identifier, []).append([self.Identifier, bus.Type])
        builder.add_node_type_property(
            name=self.Identifier, propname="ConnectorType", proptype="constant", default=self.ConnectorType
        )
        nodes.append(self.Identifier)


class OCPMezzanineSlot(OCPMezzanineSlotBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/OCPMezzanineSlots",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
            buses.setdefault(bus.Identifier, []).append([self.Identifier, bus.Type])
        builder.add_node_type_property(
            name=self.Identifier, propname="Version", proptype="constant", default=self.Version
        )
        builder.add_node_type_property(
            name=self.Identifier, propname="FormFactor", proptype="constant", default=self.FormFactor
        )
        nodes.append(self.Identifier)


class ControlPanel(ControlPanelBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        builder.add_node_type(
            name=self.Identifier,
            category="Connectors/ControlPanels",
        )
        for bus in self.ConnectedBuses:
            builder.add_node_type_interface(
                name=self.Identifier, interfacename=bus.Type, interfacetype=bus.Type.lower()
            )
            buses.setdefault(bus.Identifier, []).append([self.Identifier, bus.Type])

        nodes.append(self.Identifier)


def add_node(
    connectors: Connectors,
    prop: str,
    class_name: type,
    buses: dict,
    nodes: List[str],
    specification_builder: SpecificationBuilder,
) -> None:
    node_data = getattr(connectors, prop)[0].model_dump()
    node = class_name(**node_data)
    node.to_spec_node(buses, nodes, specification_builder)


def add_hpm_nodes_to_spec(
    connectors: Connectors, buses: dict, nodes: List[str], specification_builder: SpecificationBuilder
) -> None:
    add_node(connectors, "SOCs", Soc, buses, nodes, specification_builder)
    add_node(connectors, "MemorySubsystems", MemorySubsystem, buses, nodes, specification_builder)
    add_node(connectors, "Composites", Composite, buses, nodes, specification_builder)
    add_node(connectors, "Mxios", Mxio, buses, nodes, specification_builder)
    add_node(connectors, "Mpics", Mpic, buses, nodes, specification_builder)
    add_node(connectors, "PowerSupplies", PowerSupply, buses, nodes, specification_builder)
    add_node(connectors, "OCPMezzanineSlots", OCPMezzanineSlot, buses, nodes, specification_builder)
    add_node(connectors, "ControlPanels", ControlPanel, buses, nodes, specification_builder)
    add_node(connectors, "SCIs", Sci, buses, nodes, specification_builder)
    add_node(connectors, "Fans", Fan, buses, nodes, specification_builder)
    add_node(connectors, "RealTimeClockBatteries", RtcBattery, buses, nodes, specification_builder)
    add_node(connectors, "PowerDistributionBoards", PDB, buses, nodes, specification_builder)
