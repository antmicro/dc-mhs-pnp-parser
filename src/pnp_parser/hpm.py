from .fru_model import ConnectorsMemorySubsystem as MemorySubsystemBase

from .fru_model import ConnectorsComposite as CompositeBase

from .fru_model import ConnectorsMxio as MxioBase

from .fru_model import ConnectorsMpic as MpicBase
from .fru_model import ConnectorsPowerSupply as PowerSupplyBase
from .fru_model import ConnectorsOCPMezzanineSlot as OCPMezzanineSlotBase
from .fru_model import ConnectorsControlPanel as ControlPanelBase
from pydantic import BaseModel
from .fru_model import ConnectorsSOCs as SocBase

from .fru_model import ConnectorsSCI as SciBase
from .fru_model import ConnectorsFan as FanBase

from .fru_model import ConnectorsRealTimeClockBattery as RealTimeClockBatteryBase
from .fru_model import ConnectorsPowerDistributionBoardManagement as PDBMBase

# from .fru_model import Connectors
from dataclasses import dataclass
from pipeline_manager.specification_builder import SpecificationBuilder
from typing import Any, List, Sequence, TypeGuard

from pnp_parser.fru_model import HardwareComponent, NamedComponent


class Soc(SocBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/SoCs",
        )
        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=self.identifier.root, interfacename=bus.identifier, interfacetype=bus.type.lower()
                )
                buses.setdefault(bus.identifier, []).append((self.identifier.root, bus.type))

        nodes.append(self.identifier.root)


class Sci(SciBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        node_name = self.identifier.root
        builder.add_node_type(
            name=node_name,
            category="Connectors/SCIs",
        )
        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=node_name, interfacename=bus.identifier, interfacetype=bus.type.lower(), side="right"
                )
                buses.setdefault(bus.identifier, []).append(
                    (
                        node_name,
                        bus.type,
                    )
                )

        builder.add_node_type_property(name=node_name, propname="Revision", proptype="constant", default=self.revision)
        builder.add_node_type_property(name=node_name, propname="Version", proptype="constant", default=self.version)
        builder.add_node_type_property(
            name=node_name, propname="CommonCircuitType", proptype="constant", default=self.common_circuit_type.value
        )
        nodes.append(node_name)


class Fan(FanBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/Fans",
        )
        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=self.identifier.root, interfacename=bus.type, interfacetype=bus.type.lower()
                )
                buses.setdefault(bus.identifier, []).append((self.identifier.root, bus.type))

        builder.add_node_type_property(
            name=self.identifier.root,
            propname="MaximumPower (W)",
            proptype="constant",
            default=self.maximum_power_watts,
        )
        builder.add_node_type_property(
            name=self.identifier.root, propname="ConnectorType", proptype="constant", default=self.connector_type
        )
        builder.add_node_type_property(
            name=self.identifier.root, propname="HotPlugSuported", proptype="constant", default=self.hot_plug_supported
        )
        nodes.append(self.identifier.root)


class PDBM(PDBMBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/Power Distribution Boards",
        )
        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=self.identifier.root, interfacename=bus.type, interfacetype=bus.type.lower()
                )
                buses.setdefault(bus.identifier, []).append((self.identifier.root, bus.type))

        builder.add_node_type_property(
            name=self.identifier.root, propname="Type", proptype="constant", default=self.management_type
        )
        builder.add_node_type_property(
            name=self.identifier.root, propname="ConnectorType", proptype="constant", default=self.connector_type
        )
        nodes.append(self.identifier.root)


class MemorySubsystem(MemorySubsystemBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        for slot in self.slots:
            builder.add_node_type(
                name=slot.identifier.root,
                category="Connectors/MemorySubsystems/Slots",
            )

            if slot.connected_buses:
                for bus in slot.connected_buses.root:
                    if not bus.type:
                        continue

                    builder.add_node_type_interface(
                        name=slot.identifier.root, interfacename=bus.identifier, interfacetype=bus.type.lower()
                    )
                    buses.setdefault(bus.identifier, []).append((slot.identifier.root, bus.type))

            builder.add_node_type_property(
                name=slot.identifier.root, propname="Proximity", proptype="constant", default=slot.proximity.value
            )
            nodes.append(slot.identifier.root)


class Composite(CompositeBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/Composites",
        )
        builder.add_node_type_interface(
            name=self.identifier.root, interfacename=self.connector_type, interfacetype=self.connector_type.lower()
        )
        builder.add_node_type_property(
            name=self.identifier.root, propname="Type", proptype="constant", default=self.connector_type
        )
        nodes.append(self.identifier.root)


class Mxio(MxioBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/MPICs",
        )

        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=self.identifier.root, interfacename=bus.identifier, interfacetype=bus.type.lower()
                )
                buses.setdefault(bus.identifier, []).append((self.identifier.root, bus.type))

        builder.add_node_type_property(
            name=self.identifier.root, propname="ConnectorType", proptype="constant", default=self.connector_type
        )
        nodes.append(self.identifier.root)


class Mpic(MpicBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/MXIOs",
        )
        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=self.identifier.root, interfacename=bus.type, interfacetype=bus.type.lower()
                )
                buses.setdefault(bus.identifier, []).append((self.identifier.root, bus.type))

        builder.add_node_type_property(
            name=self.identifier.root, propname="ConnectorType", proptype="constant", default=self.connector_type
        )
        if self.adjusted_maximum_actual_power_supported_watts:
            builder.add_node_type_property(
                name=self.identifier.root,
                propname="AdjustedMaximumActualPowerSupportedWatts",
                proptype="constant",
                default=str(self.adjusted_maximum_actual_power_supported_watts),
            )

        nodes.append(self.identifier.root)


class RtcBattery(RealTimeClockBatteryBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/RTC Batteries",
        )
        nodes.append(self.identifier.root)


class PowerSupply(PowerSupplyBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/Power Supplies",
        )
        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=self.identifier.root, interfacename=bus.type, interfacetype=bus.type.lower()
                )
                buses.setdefault(bus.identifier, []).append((self.identifier.root, bus.type))

        builder.add_node_type_property(
            name=self.identifier.root, propname="ConnectorType", proptype="constant", default=self.connector_type
        )
        nodes.append(self.identifier.root)


class OCPMezzanineSlot(OCPMezzanineSlotBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/OCPMezzanineSlots",
        )
        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=self.identifier.root, interfacename=bus.type, interfacetype=bus.type.lower()
                )
                buses.setdefault(bus.identifier, []).append((self.identifier.root, bus.type))

        builder.add_node_type_property(
            name=self.identifier.root, propname="Version", proptype="constant", default=self.version
        )
        builder.add_node_type_property(
            name=self.identifier.root, propname="FormFactor", proptype="constant", default=self.form_factor.value
        )
        nodes.append(self.identifier.root)


class ControlPanel(ControlPanelBase):
    def to_spec_node(
        self, nodes: list[str], buses: dict[str, list[tuple[str, str]]], builder: SpecificationBuilder
    ) -> None:
        builder.add_node_type(
            name=self.identifier.root,
            category="Connectors/ControlPanels",
        )
        if self.connected_buses:
            for bus in self.connected_buses.root:
                if not bus.type:
                    continue

                builder.add_node_type_interface(
                    name=self.identifier.root, interfacename=bus.type, interfacetype=bus.type.lower()
                )
                buses.setdefault(bus.identifier, []).append((self.identifier.root, bus.type))

        nodes.append(self.identifier.root)


def add_nodes(
    entities: Sequence[BaseModel],
    class_name: type,
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    specification_builder: SpecificationBuilder,
) -> None:
    for entity in entities:
        node_data = entity.model_dump(by_alias=True)
        node = class_name(**node_data)  # pyright: ignore[reportAny]
        node.to_spec_node(nodes, buses, specification_builder)  # pyright: ignore[reportAny]


def add_hpm_nodes_to_spec(
    hpm: HardwareComponent,
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    specification_builder: SpecificationBuilder,
) -> None:
    connectors = hpm.component.connectors
    add_nodes(connectors.socs or [], Soc, nodes, buses, specification_builder)
    add_nodes(connectors.memory_subsystems or [], MemorySubsystem, nodes, buses, specification_builder)
    add_nodes(connectors.composites or [], Composite, nodes, buses, specification_builder)
    add_nodes(connectors.mxios or [], Mxio, nodes, buses, specification_builder)
    add_nodes(connectors.mpics or [], Mpic, nodes, buses, specification_builder)
    add_nodes(connectors.power_supplies or [], PowerSupply, nodes, buses, specification_builder)
    add_nodes(connectors.ocp_mezzanine_slots or [], OCPMezzanineSlot, nodes, buses, specification_builder)
    add_nodes(connectors.control_panels or [], ControlPanel, nodes, buses, specification_builder)
    add_nodes(connectors.scis or [], Sci, nodes, buses, specification_builder)
    add_nodes(connectors.fans or [], Fan, nodes, buses, specification_builder)
    add_nodes(connectors.real_time_clock_batteries or [], RtcBattery, nodes, buses, specification_builder)
    add_nodes(connectors.power_distribution_board_managements or [], PDBM, nodes, buses, specification_builder)
