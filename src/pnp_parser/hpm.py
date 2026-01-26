from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from itertools import combinations
import math
import random
from typing import Any, Iterable, Sequence, TypeGuard, TypeVar
from pipeline_manager.dataflow_builder.data_structures import DataflowBuilderError, Side
from typing_extensions import TypeIs

from pipeline_manager.dataflow_builder.dataflow_graph import AttributeType, DataflowGraph
from pipeline_manager.dataflow_builder.entities import Interface, Node, Vector2
from pipeline_manager.specification_builder import SpecificationBuilder
from pydantic import BaseModel

from .fru_model import (
    Bus,
    BusWithConnections,
    BusWithSegments,
    Buses,
    BusesESPI,
    BusesI2C,
    BusesI3C,
    BusesJTAG,
    BusesLTPI,
    BusesMPESTI,
    BusesNCSIRBT,
    BusesPCIe,
    BusesPECI,
    BusesQSPI,
    BusesSGMII,
    BusesSGPIO,
    BusesSPI,
    BusesUART,
    BusesUSB,
    Connector,
    ConnectorWithSignals,
    ConnectorsComposite,
    ConnectorsMemorySubsystem,
    ConnectorsMpic,
    ConnectorsMxio,
    HardwareComponent,
    Connectors,
    Devices,
    Hub,
    HubI3C,
    HubUSB,
    MuX,
    MuXI2C,
    MuXI3C,
    MuXJTAG,
    MuXUART,
    MuXUSB,
    ReferencedBusListItem,
    Segment,
    SegmentI2C,
    SegmentI3C,
    SegmentJTAG,
    SegmentNCSIRBT,
    SegmentUART,
    SegmentUSB,
    SegmentWithHubs,
    SegmentWithMuXes,
    Slot,
)


segment_categories: dict[type[Segment], str] = {
    SegmentI2C: "I2C",
    SegmentI3C: "I3C",
    SegmentJTAG: "JTAG",
    SegmentUSB: "USB",
    SegmentNCSIRBT: "NCSI-RBT",
    SegmentUART: "UART",
}

hub_categories: dict[type[Hub], str] = {
    HubI3C: "I3C",
    HubUSB: "USB",
}

mux_categories: dict[type[MuX], str] = {
    MuXI2C: "I2C",
    MuXI3C: "I3C",
    MuXJTAG: "JTAG",
    MuXUSB: "USB",
    MuXUART: "UART",
}

bus_names: dict[type[Bus], str] = {
    BusesESPI: "ESPI",
    BusesI2C: "I2C",
    BusesI3C: "I3C",
    BusesJTAG: "JTAG",
    BusesLTPI: "LTPI",
    BusesMPESTI: "MPESTI",
    BusesNCSIRBT: "NCSI-RBT",
    BusesPCIe: "PCIe",
    BusesPECI: "PECI",
    BusesQSPI: "QSPI",
    BusesSGMII: "SGMII",
    BusesSPI: "SPI",
    BusesSGPIO: "SGPIO",
    BusesUART: "UART",
    BusesUSB: "USB",
}

connector_categories = {
    "socs": "Connectors/SoC",
    "memory_subsystems": "Connectors/Memory Subsystem",
    "composites": "Connectors/Composite",
    "cooling_subsystems": "Connectors/Cooling Subsystem",
    "drives": "Connectors/Drive",
    "mxios": "Connectors/MXIO",
    "mpics": "Connectors/MPIC",
    "ocp_mezzanine_slots": "Connectors/OCP Mezzanine Slot",
    "power_supplies": "Connectors/Power Supply",
    "control_panels": "Connectors/Control Panel",
    "pcie_cems": "Connectors/PCIe CEM",
    "power_distribution_board_managements": "Connectors/PDB Management",
    "real_time_clock_batteries": "Connectors/RTC Battery",
    "fans": "Connectors/Fan",
    "scis": "Connectors/SCI",
    "intrusion_detection": "Connectors/Intrusion detection",
    "physical_usbs": "Connectors/USB",
    "oem": "Connectors/OEM",
}


def set_node_attributes(model: BaseModel, node_name: str, spec_builder: SpecificationBuilder):
    for attr, attr_field_info in type(model).model_fields.items():
        attr_value = getattr(model, attr, None)

        valid_attr_value = isinstance(attr_value, (int, str, bool, Enum))
        if not valid_attr_value:
            continue

        if isinstance(attr_value, Enum):
            attr_value = attr_value.value

        spec_builder.add_node_type_property(
            name=node_name,
            propname=attr_field_info.alias or attr,
            proptype="constant",
            default=str(attr_value),
        )


def get_node_interface(node_name: str, interface_name: str, graph_nodes: dict[str, Node]) -> Interface:
    node = graph_nodes[node_name]
    [interface] = node.get_interfaces_by_regex(f"^{interface_name}$")
    return interface


def add_connector_node(
    connector: Connector,
    field: str,
    physical_signals: defaultdict[str, list[str]],
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    node_layers: dict[str, str],
    spec_builder: SpecificationBuilder,
) -> None:
    category = connector_categories[field]

    if isinstance(connector, ConnectorsMemorySubsystem):
        return

    identifier = connector.identifier.root

    bus_list = []
    if not isinstance(connector, ConnectorsComposite):
        connected_buses = connector.connected_buses
        if connected_buses:
            for bus in connected_buses.root:
                if not bus.type:
                    continue

                bus_list.append(bus)

    spec_builder.add_node_type(name=identifier, category=category)

    for bus in bus_list:
        spec_builder.add_node_type_interface(
            name=identifier, interfacename=bus.identifier, interfacetype=bus.type.lower(), maxcount=-1
        )
        buses.setdefault(bus.identifier, []).append((identifier, bus.type))

    for signal_name in physical_signals[identifier]:
        spec_builder.add_node_type_interface(name=identifier, interfacename=signal_name, interfacetype="signal")

    set_node_attributes(connector, identifier, spec_builder)

    nodes.append(identifier)


def add_composite_connector_node_interfaces(
    composites: list[ConnectorsComposite],
    mpics: list[ConnectorsMpic],
    mxios: list[ConnectorsMxio],
    spec_builder: SpecificationBuilder,
) -> None:
    mpic_buses: defaultdict[str, list[ReferencedBusListItem]] = defaultdict(list)
    mxio_buses: defaultdict[str, list[ReferencedBusListItem]] = defaultdict(list)

    for mpic in mpics:
        connected_buses = mpic.connected_buses
        if connected_buses:
            mpic_buses[mpic.identifier.root].extend(connected_buses.root)

    for mxio in mxios:
        connected_buses = mxio.connected_buses
        if connected_buses:
            mxio_buses[mxio.identifier.root].extend(connected_buses.root)

    for composite in composites:
        composite_mpic_buses = [bus for mpic_name in composite.mpics for bus in mpic_buses[mpic_name]]
        composite_mxio_buses = [bus for mxio_name in composite.mxios for bus in mxio_buses[mxio_name]]
        added_buses: set[str] = set()

        for bus in composite_mpic_buses + composite_mxio_buses:
            if not bus.type or bus.identifier in added_buses:
                continue

            added_buses.add(bus.identifier)
            spec_builder.add_node_type_interface(
                name=composite.identifier.root, interfacename=bus.identifier, interfacetype=bus.type.lower()
            )


def add_memory_subsystem_slot_node(slot: Slot, nodes: list[str], spec_builder: SpecificationBuilder) -> None:
    identifier = slot.identifier.root

    spec_builder.add_node_type(name=identifier, category="Connectors/DIMM Slots")

    connected_buses = getattr(slot, "connected_buses", None)
    if connected_buses:
        for bus in connected_buses.root:
            if not bus.type:
                continue

            spec_builder.add_node_type_interface(
                name=identifier, interfacename=bus.identifier, interfacetype=bus.type.lower()
            )

    set_node_attributes(slot, identifier, spec_builder)

    nodes.append(identifier)


def add_connector_nodes(
    connectors: Connectors,
    physical_signals: defaultdict[str, list[str]],
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    node_layers: dict[str, str],
    spec_builder: SpecificationBuilder,
) -> None:
    for field in Connectors.model_fields:
        connector_list = getattr(connectors, field)

        if not is_connector_list(connector_list):
            continue

        for connector in connector_list:
            add_connector_node(connector, field, physical_signals, nodes, buses, node_layers, spec_builder)

    add_composite_connector_node_interfaces(
        connectors.composites or [], connectors.mpics or [], connectors.mxios or [], spec_builder
    )

    for memory_subsystem in connectors.memory_subsystems or []:
        for slot in memory_subsystem.slots:
            add_memory_subsystem_slot_node(slot, nodes, spec_builder)


def get_physical_signals(devices: Devices, connectors: Connectors) -> defaultdict[str, list[str]]:
    physical_signals: defaultdict[str, list[str]] = defaultdict(list)

    for device in devices.root:
        device_name = device.identifier.root

        for signal in device.physical_signals or []:
            if not signal.type_id or not signal.subtype_id:
                continue

            target_name = signal.type_id.root
            signal_name = signal.subtype_id.root

            physical_signals[device_name].append(signal_name)
            physical_signals[target_name].append(signal_name)

    connectors_with_signals: Iterable[ConnectorWithSignals] = (
        connector
        for connectors_type in (
            connectors.scis or [],
            connectors.pcie_cems or [],
            connectors.ocp_mezzanine_slots or [],
            connectors.mxios or [],
        )
        for connector in connectors_type
    )

    for connector in connectors_with_signals:
        connector_name = connector.identifier.root

        for signal in connector.signals or []:
            if not signal.type_id or not signal.subtype_id:
                continue

            target_name = signal.type_id.root
            signal_name = signal.subtype_id.root

            physical_signals[connector_name].append(signal_name)
            physical_signals[target_name].append(signal_name)

    return physical_signals


def add_device_nodes(
    devices: Devices,
    physical_signals: defaultdict[str, list[str]],
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    for device in devices.root:
        node_name = device.identifier.root

        if not device.type:
            continue

        spec_builder.add_node_type(name=node_name, category=f"Devices/{device.type}")

        added_interfaces: set[str] = set()

        if device.connected_buses:
            for connected_bus in device.connected_buses.root:
                if not connected_bus.type:
                    continue

                spec_builder.add_node_type_interface(
                    name=node_name, interfacename=connected_bus.identifier, interfacetype=connected_bus.type.lower()
                )
                added_interfaces.add(connected_bus.identifier)

        for signal_name in physical_signals[node_name]:
            if signal_name not in added_interfaces:
                spec_builder.add_node_type_interface(name=node_name, interfacename=signal_name, interfacetype="signal")
                added_interfaces.add(signal_name)

        if device.manufacturers:
            spec_builder.add_node_type_property(
                name=node_name,
                propname="Vendor",
                proptype="constant",
                default=device.manufacturers.root[0],
            )

        if device.models:
            spec_builder.add_node_type_property(
                name=node_name, propname="Model", proptype="constant", default=device.models.root[0]
            )

        nodes.append(node_name)


def add_segment(
    segment: Segment,
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    segment_name = segment.identifier.root
    bus_category = segment_categories[type(segment)]
    spec_builder.add_node_type(
        name=segment_name, category=f"{bus_category}/Segments/{segment_name}", layer=bus_category
    )

    set_node_attributes(segment, segment_name, spec_builder)

    spec_builder.add_node_type_interface(
        name=segment_name, interfacename=segment_name, interfacetype=bus_category.lower(), side="right", maxcount=-1
    )

    nodes.append(segment_name)


def add_hub(
    hub: Hub,
    input_segment_name: str,
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    hub_name = hub.identifier.root
    bus_category = hub_categories[type(hub)]
    spec_builder.add_node_type(name=hub_name, category=f"{bus_category}/Hubs/{hub_name}", layer=bus_category)

    set_node_attributes(hub, hub_name, spec_builder)

    if hub.manufacturers:
        spec_builder.add_node_type_property(
            name=hub_name, propname="Manufacturer", proptype="constant", default=hub.manufacturers.root[0]
        )

    if hub.models:
        spec_builder.add_node_type_property(
            name=hub_name, propname="Model", proptype="constant", default=hub.models.root[0]
        )

    spec_builder.add_node_type_interface(
        name=hub_name, interfacename=input_segment_name, interfacetype=bus_category.lower(), side="left"
    )

    for port in hub.ports:
        output_segment_name = port.endpoint.root
        spec_builder.add_node_type_interface(
            name=hub_name, interfacename=output_segment_name, interfacetype=bus_category.lower(), side="right"
        )

    nodes.append(hub_name)


def add_mux(
    mux: MuX,
    input_segment_name: str,
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    mux_name = mux.identifier.root
    bus_category = mux_categories[type(mux)]
    spec_builder.add_node_type(name=mux_name, category=f"{bus_category}/MUXes/{mux_name}", layer=bus_category)

    set_node_attributes(mux, mux_name, spec_builder)

    if isinstance(mux, (MuXI2C, MuXI3C)):
        spec_builder.add_node_type_property(
            name=mux_name, propname="Manufacturer", proptype="constant", default=mux.manufacturers.root[0]
        )

        if mux.models:
            spec_builder.add_node_type_property(
                name=mux_name, propname="Model", proptype="constant", default=mux.models.root[0]
            )

    spec_builder.add_node_type_interface(
        name=mux_name, interfacename=input_segment_name, interfacetype=bus_category.lower(), side="left"
    )

    for channel in mux.channels:
        output_segment_name = channel.endpoint.root
        spec_builder.add_node_type_interface(
            name=mux_name, interfacename=output_segment_name, interfacetype=bus_category.lower(), side="right"
        )

    nodes.append(mux_name)


def add_bus_nodes(
    buses: Sequence[Bus],
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    for bus in buses:
        if isinstance(bus, BusWithSegments):
            for segment in bus.segments:
                input_segment_name = segment.identifier.root
                add_segment(segment, nodes, spec_builder)

                if isinstance(segment, SegmentWithHubs):
                    for hub in segment.hubs or []:
                        add_hub(hub, input_segment_name, nodes, spec_builder)

                if isinstance(segment, SegmentWithMuXes):
                    for mux in segment.muxes or []:
                        add_mux(mux, input_segment_name, nodes, spec_builder)


def is_connector_list(x: Any) -> TypeIs[list[Connector]]:
    return isinstance(x, list) and all(isinstance(x_elem, Connector) for x_elem in x)


def is_bus_list(x: Any) -> TypeIs[list[Bus]]:
    return isinstance(x, list) and all(isinstance(x_elem, Bus) for x_elem in x)


def get_connectors(hpm: HardwareComponent) -> list[Connector]:
    all_connectors_list: list[Connector] = []

    for bus_list_name in Connectors.model_fields:
        field_value = getattr(hpm.component.buses, bus_list_name)

        if is_connector_list(field_value):
            all_connectors_list.extend(field_value)

    return all_connectors_list


def get_buses(hpm: HardwareComponent) -> list[Bus]:
    all_buses_list: list[Bus] = []

    for bus_list_name in Buses.model_fields:
        field_value = getattr(hpm.component.buses, bus_list_name)

        if is_bus_list(field_value):
            all_buses_list.extend(field_value)

    return all_buses_list


def add_hpm_nodes_to_spec(
    hpm: HardwareComponent,
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    specification_builder: SpecificationBuilder,
) -> None:
    devices = hpm.component.devices
    connectors = hpm.component.connectors
    node_layers: dict[str, str] = {}

    physical_signals = get_physical_signals(devices, connectors)

    add_device_nodes(devices, physical_signals, nodes, specification_builder)
    add_connector_nodes(connectors, physical_signals, nodes, buses, node_layers, specification_builder)

    add_bus_nodes(get_buses(hpm), nodes, specification_builder)


def add_hpm_layers_to_spec(
    specification_builder: SpecificationBuilder,
):
    for bus_name in bus_names.values():
        specification_builder.metadata_add_layer(bus_name, nodelayers=[bus_name], nodeinterfaces=[bus_name])

    specification_builder.metadata_add_layer("Signal", nodeinterfaces=["Signal"])


def connect_bus_connectors_devices(
    bus: BusWithConnections, hpm_graph: DataflowGraph, graph_nodes: dict[str, Node]
) -> None:
    bus_name = bus.identifier.root

    # HPM FRU JSON mockup file cases:
    # 1. one connector, one device
    # 2. two connectors, 0/1 devices

    device_interfaces = (
        [get_node_interface(device.endpoint, bus_name, graph_nodes) for device in bus.connected_devices.root]
        if bus.connected_devices
        else []
    )

    connector_interfaces = (
        [get_node_interface(connector.endpoint, bus_name, graph_nodes) for connector in bus.connectors.root]
        if bus.connectors
        else []
    )

    # Connect device to connectors
    # In the HPM FRU JSON mockup file if there are connectors then there is at most one device defined
    # (1-to-n connections if correct, n-to-n otherwise)
    for device_interface in device_interfaces:
        for connector_interface in connector_interfaces:
            hpm_graph.create_connection(device_interface, connector_interface)

    # Connect devices to each other
    # Shouldn't run since in the HPM FRU JSON mockup file there is at most one device defined
    # (no connections if correct, n-to-n otherwise)
    for device1_interface, device2_interface in combinations(device_interfaces, 2):
        hpm_graph.create_connection(device1_interface, device2_interface)

    if not device_interfaces:
        # Connect connectors to each other
        # In the HPM FRU mockup JSON if there are no devices then there are two connectors
        # (1-to-1 connection assuming there are two connectors, otherwise n-to-n)
        for connector1_interface, connector2_interface in combinations(connector_interfaces, 2):
            hpm_graph.create_connection(connector1_interface, connector2_interface)


def connect_segment_connectors(
    bus_name: str,
    segment: Segment,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not segment.connectors:
        return

    segment_node = graph_nodes[segment.identifier.root]
    [segment_interface] = segment_node.get_interfaces_by_regex(f"{bus_name}")

    connectors = segment.connectors.root
    for connector in connectors:
        connector_node = graph_nodes[connector.endpoint]
        [connector_interface] = connector_node.get_interfaces_by_regex(bus_name)

        hpm_graph.create_connection(connector_interface, segment_interface)


def connect_segment_devices(
    bus_name: str,
    segment: Segment,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not segment.connected_devices:
        return

    segment_node = graph_nodes[segment.identifier.root]
    [segment_interface] = segment_node.get_interfaces_by_regex(f"{bus_name}")

    devices = segment.connected_devices.root
    for device in devices:
        device_node = graph_nodes[device.endpoint]
        [device_interface] = device_node.get_interfaces_by_regex(f"^{bus_name}$")

        hpm_graph.create_connection(device_interface, segment_interface)


def connect_segment_muxes(
    segment: SegmentWithMuXes,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not segment.muxes:
        return

    input_segment_name = segment.identifier.root
    input_segment_node = graph_nodes[input_segment_name]
    [input_segment_interface] = input_segment_node.get_interfaces_by_regex(input_segment_name)

    for mux in segment.muxes:
        mux_name = mux.identifier.root
        mux_node = graph_nodes[mux_name]

        [mux_input_interface] = mux_node.get_interfaces_by_regex(input_segment_name)

        hpm_graph.create_connection(input_segment_interface, mux_input_interface)

        for channel in mux.channels:
            output_segment_name = channel.endpoint.root
            output_segment_node = graph_nodes[output_segment_name]
            [output_segment_interface] = output_segment_node.get_interfaces_by_regex(output_segment_name)

            [mux_output_interface] = mux_node.get_interfaces_by_regex(output_segment_name)

            hpm_graph.create_connection(mux_output_interface, output_segment_interface)


def connect_segment_hubs(
    segment: SegmentWithHubs,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not segment.hubs:
        return

    input_segment_name = segment.identifier.root
    input_segment_node = graph_nodes[input_segment_name]
    [input_segment_interface] = input_segment_node.get_interfaces_by_regex(input_segment_name)

    for hub in segment.hubs:
        hub_name = hub.identifier.root
        hub_node = graph_nodes[hub_name]

        [hub_input_interface] = hub_node.get_interfaces_by_regex(input_segment_name)

        hpm_graph.create_connection(input_segment_interface, hub_input_interface)

        for port in hub.ports:
            output_segment_name = port.endpoint.root
            output_segment_node = graph_nodes[output_segment_name]
            [output_segment_interface] = output_segment_node.get_interfaces_by_regex(output_segment_name)

            [hub_output_interface] = hub_node.get_interfaces_by_regex(output_segment_name)

            hpm_graph.create_connection(hub_output_interface, output_segment_interface)


def get_segment_interfaces(bus_name: str, segment: Segment, graph_nodes: dict[str, Node]) -> list[Interface]:
    if not segment.connectors:
        return []

    connectors = segment.connectors.root
    connector_interfaces = []

    for connector in connectors:
        connector_node = graph_nodes[connector.endpoint]
        [connector_interface] = connector_node.get_interfaces_by_regex(bus_name)
        connector_interfaces.append(connector_interface)

    return connector_interfaces


def add_bus_connections(
    buses: list[Bus],
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    for bus in buses:
        bus_name = bus.identifier.root

        if isinstance(bus, BusWithConnections):
            connect_bus_connectors_devices(bus, hpm_graph, graph_nodes)

        if isinstance(bus, BusWithSegments):
            for segment in bus.segments:
                connect_segment_connectors(bus_name, segment, hpm_graph, graph_nodes)
                connect_segment_devices(bus_name, segment, hpm_graph, graph_nodes)

                if isinstance(segment, SegmentWithMuXes):
                    connect_segment_muxes(segment, hpm_graph, graph_nodes)

                if isinstance(segment, SegmentWithHubs):
                    connect_segment_hubs(segment, hpm_graph, graph_nodes)


def add_composite_connections(
    composites: list[ConnectorsComposite],
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    for composite in composites:
        composite_name = composite.identifier.root
        composite_node = graph_nodes[composite_name]

        for mpic_name in composite.mpics:
            mpic_node = graph_nodes[mpic_name]
            [mpic_interface] = mpic_node.get_interfaces_by_regex("MPESTI-")
            [composite_interface] = composite_node.get_interfaces_by_regex(mpic_interface.name)

            hpm_graph.create_connection(composite_interface, mpic_interface)

        for mxio_name in composite.mxios:
            mxio_node = graph_nodes[mxio_name]
            [mxio_interface] = mxio_node.get_interfaces_by_regex("MPESTI-")
            [composite_interface] = composite_node.get_interfaces_by_regex(mxio_interface.name)

            hpm_graph.create_connection(composite_interface, mxio_interface)


def add_signal_connections(
    connectors: Connectors,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    connectors_with_signals: Iterable[ConnectorWithSignals] = (
        connector
        for connectors_type in (
            connectors.scis or [],
            connectors.pcie_cems or [],
            connectors.ocp_mezzanine_slots or [],
            connectors.mxios or [],
        )
        for connector in connectors_type
    )

    for connector in connectors_with_signals:
        connector_name = connector.identifier.root
        connector_node = graph_nodes[connector_name]

        for signal in connector.signals or []:
            if not signal.type_id or not signal.subtype_id:
                continue

            signal_name = signal.subtype_id.root

            target_name = signal.type_id.root
            target_node = graph_nodes[target_name]

            [connector_interface] = connector_node.get_interfaces_by_regex(signal_name)
            [target_interface] = target_node.get_interfaces_by_regex(f"^{signal_name}$")

            hpm_graph.create_connection(connector_interface, target_interface)


def add_hpm_graph_connections(
    hpm: HardwareComponent,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    buses = hpm.component.buses
    if not buses:
        return

    add_bus_connections(get_buses(hpm), hpm_graph, graph_nodes)

    composites = hpm.component.connectors.composites or []
    add_composite_connections(composites, hpm_graph, graph_nodes)

    connectors = hpm.component.connectors
    add_signal_connections(connectors, hpm_graph, graph_nodes)


T = TypeVar("T")


def force_type(x: object, type: type[T]) -> TypeGuard[T]:
    return True


NodeID = str
InterfaceID = str


def get_node_interface_connections(graph: DataflowGraph) -> dict[NodeID, list[tuple[InterfaceID, list[Interface]]]]:
    node_to_interface_connections = {
        node.id: [
            (
                interface.id,
                [
                    connection.to_interface
                    for connection in graph._connections.values()
                    if connection.from_interface == interface
                ]
                + [
                    connection.from_interface
                    for connection in graph._connections.values()
                    if connection.to_interface == interface
                ],
            )
            for interface in node.interfaces
        ]
        for node in graph._nodes.values()
    }

    return node_to_interface_connections


def get_interface_parent_nodes(graph: DataflowGraph) -> dict[InterfaceID, Node]:
    interface_parent_nodes: dict[InterfaceID, Node] = {}

    for node in graph._nodes.values():
        for interface in node.interfaces:
            interface_parent_nodes[interface.id] = node

    return interface_parent_nodes


def approximate_node_height(node: Node) -> float:
    left_interfaces_height = 0
    right_interfaces_height = 0

    interface_padding = 15
    interface_line_height = 19

    for interface in node.interfaces:
        lines = 1 + (len(interface.name) - 1) // 14  # assuming wrapping every 14 characters

        if not interface.side or interface.side == Side.LEFT:
            left_interfaces_height += lines * interface_line_height + interface_padding
        else:
            right_interfaces_height += lines * interface_line_height + interface_padding

    num_properties = len(node.properties)

    title_height = 60
    content_padding = 22.5
    properties_height = 53 * num_properties
    interfaces_height = max(left_interfaces_height, right_interfaces_height)

    approx_height = title_height + content_padding + properties_height + interfaces_height
    return approx_height


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    @staticmethod
    def union(bb1: "BoundingBox", bb2: "BoundingBox") -> "BoundingBox":
        x1 = min(bb1.x, bb2.x)
        y1 = min(bb1.y, bb2.y)
        x2 = max(bb1.x + bb1.width, bb2.x + bb2.width)
        y2 = max(bb1.y + bb1.height, bb2.y + bb2.height)

        return BoundingBox(x1, y1, x2 - x1, y2 - y1)


def get_node_bounding_box(node: Node) -> BoundingBox:
    position = node.position or Vector2()
    return BoundingBox(position.x, position.y, 300, approximate_node_height(node))


def place_node_tree(
    graph: DataflowGraph,
    node: Node,
    x: float,
    y: float,
    placed_nodes: set[NodeID],
    interface_connections: dict[NodeID, list[tuple[InterfaceID, list[Interface]]]],
    interface_parent_nodes: dict[InterfaceID, Node],
    node_connected_nodes: dict[NodeID, set[NodeID]],
) -> BoundingBox:
    placed_nodes.add(node.id)

    offset = 100

    new_x = x
    start_y = y + approximate_node_height(node) + offset
    new_y = start_y
    bounding_box: BoundingBox | None = None

    left_interfaces: list[Interface] = []
    right_interfaces: list[Interface] = []

    for from_interface_id, to_interfaces in interface_connections[node.id]:
        if graph._get_interfaces(id=from_interface_id)[0].side != Side.RIGHT:
            left_interfaces.extend(to_interfaces)
        else:
            right_interfaces.extend(to_interfaces)

    right_interfaces = right_interfaces[::-1]

    for left_interface in left_interfaces:
        interface_connections[node.id] = [
            (from_interface, to_interface)
            for from_interface, to_interface in interface_connections[node.id]
            if to_interface != left_interface
        ]
        to_node = interface_parent_nodes[left_interface.id]

        if to_node.id in placed_nodes:
            continue

        children_bounding_box = place_node_tree(
            graph,
            to_node,
            new_x,
            new_y,
            placed_nodes,
            interface_connections,
            interface_parent_nodes,
            node_connected_nodes,
        )
        bounding_box = BoundingBox.union(bounding_box, children_bounding_box) if bounding_box else children_bounding_box
        new_x += children_bounding_box.width + offset
        new_y += offset

    node.position = Vector2(new_x, y)
    new_x += 150 + offset
    new_y = start_y + (len(right_interfaces) - 1) * offset

    for right_interface in right_interfaces:
        interface_connections[node.id] = [
            (from_interface, to_interface)
            for from_interface, to_interface in interface_connections[node.id]
            if to_interface != right_interface
        ]
        to_node = interface_parent_nodes[right_interface.id]

        if to_node.id in placed_nodes:
            continue

        children_bounding_box = place_node_tree(
            graph,
            to_node,
            new_x,
            new_y,
            placed_nodes,
            interface_connections,
            interface_parent_nodes,
            node_connected_nodes,
        )
        bounding_box = BoundingBox.union(bounding_box, children_bounding_box) if bounding_box else children_bounding_box
        new_x += children_bounding_box.width + offset
        new_y -= offset

    node_bounding_box = get_node_bounding_box(node)
    return BoundingBox.union(bounding_box, node_bounding_box) if bounding_box else node_bounding_box


def get_node_connected_nodes(
    hpm_graph: DataflowGraph,
    interface_connections: dict[NodeID, list[tuple[InterfaceID, list[Interface]]]],
    interface_parent_nodes: dict[InterfaceID, Node],
) -> dict[NodeID, set[NodeID]]:
    return {
        node_id: {
            interface_parent_nodes[interface.id].id
            for interfaces in (interfaces for _, interfaces in interface_connections[node_id])
            for interface in interfaces
        }
        for node_id in hpm_graph._nodes.keys()
    }


def get_all_connected_nodes(
    graph: DataflowGraph,
    node_id: NodeID,
    node_connected_nodes: dict[NodeID, set[NodeID]],
    connected_nodes: set[NodeID] | None = None,
) -> set[NodeID]:
    if connected_nodes is None:
        connected_nodes = set()

    connected_nodes.add(node_id)

    for connected_node_id in node_connected_nodes[node_id]:
        if connected_node_id in connected_nodes:
            continue

        get_all_connected_nodes(graph, connected_node_id, node_connected_nodes, connected_nodes)

    return connected_nodes


def place_hpm_graph_nodes_tree(hpm_graph: DataflowGraph) -> None:
    # Use the node with the most interface connections as the root node
    interface_connections = get_node_interface_connections(hpm_graph)
    interface_parent_nodes = get_interface_parent_nodes(hpm_graph)
    node_connected_nodes = get_node_connected_nodes(hpm_graph, interface_connections, interface_parent_nodes)

    def connected_interface_count(node: Node) -> int:
        return sum(len(interfaces) for _, interfaces in interface_connections[node.id])

    root_node = max(hpm_graph._nodes.values(), key=connected_interface_count)

    sorted_nodes = sorted(
        ((node, connected_interface_count(node)) for node in hpm_graph._nodes.values()), key=lambda x: x[1]
    )

    place_node_tree(
        hpm_graph, root_node, 0, 0, set(), interface_connections, interface_parent_nodes, node_connected_nodes
    )


def place_hpm_graph_nodes_fewest_connections(hpm_graph: DataflowGraph) -> None:
    interface_connections = get_node_interface_connections(hpm_graph)
    interface_parent_nodes = get_interface_parent_nodes(hpm_graph)
    node_connected_nodes = get_node_connected_nodes(hpm_graph, interface_connections, interface_parent_nodes)

    x = 0

    node_connected_nodes = {
        node_id: connected_nodes
        for node_id, connected_nodes in node_connected_nodes.items()
        if len(connected_nodes) > 0
    }

    node_priorities = {node_id: -1 for node_id in hpm_graph._nodes.keys()}

    i = 0
    best_nodes = list(node_connected_nodes.items())
    while True:
        best_nodes = sorted(best_nodes, key=lambda x: (len(x[1]), node_priorities[x[0]]))
        if not best_nodes:
            break

        node_id, connected_nodes = best_nodes[0]
        node = hpm_graph._nodes[node_id]
        node.position = Vector2(800 * i, 800 * i)

        for connected_node_id in connected_nodes:
            node_priorities[connected_node_id] = i

        best_nodes.pop(0)
        print(node.name, connected_nodes)
        i -= 1

    print("-" * 80)


def place_hpm_graph_nodes_line(hpm_graph: DataflowGraph):
    interface_connections = get_node_interface_connections(hpm_graph)
    interface_parent_nodes = get_interface_parent_nodes(hpm_graph)
    node_connected_nodes = get_node_connected_nodes(hpm_graph, interface_connections, interface_parent_nodes)

    nodes_order: list[NodeID] = [node_id for node_id in hpm_graph._nodes.keys()]

    def get_score(nodes_order: list[NodeID]) -> int:
        return sum(
            abs(nodes_order.index(node_id) - nodes_order.index(connected_node_id))
            for node_id in nodes_order
            for connected_node_id in node_connected_nodes[node_id]
        )

    score = get_score(nodes_order)
    print(f"Score: {score}")

    rnd = random.Random(95638)

    for j in range(10000):
        if j % 100 == 0:
            print(f"Iteration {j}")

        new_nodes_order = nodes_order[:]
        rnd.shuffle(new_nodes_order)

        new_score = get_score(new_nodes_order)
        if new_score < score:
            print(f"Score: {new_score}")
            score = new_score


def place_hpm_graph_nodes_grid(hpm_graph: DataflowGraph):
    interface_connections = get_node_interface_connections(hpm_graph)
    interface_parent_nodes = get_interface_parent_nodes(hpm_graph)
    node_connected_nodes = get_node_connected_nodes(hpm_graph, interface_connections, interface_parent_nodes)

    rnd = random.Random(95638)

    node_ids = [node_id for node_id in hpm_graph._nodes.keys()]
    node_positions: dict[NodeID, tuple[float, float]] = {node_id: (rnd.random(), rnd.random()) for node_id in node_ids}

    def get_score(node_positions: dict[NodeID, tuple[float, float]]) -> float:
        score = 0.0

        for node_id, node_position in node_positions.items():
            node_x, node_y = node_positions[node_id]
            connected_nodes = node_connected_nodes[node_id]

            for connected_node_id in connected_nodes:
                connected_node_x, connected_node_y = node_positions[connected_node_id]

                score += math.hypot(node_x - connected_node_x, node_y - connected_node_y)

        return score

    def random_shift(position: tuple[float, float]) -> tuple[float, float]:
        x, y = position
        return (x + rnd.random(), y + rnd.random())

    def move_closer_to_connected(
        node_positions: dict[NodeID, tuple[float, float]],
    ) -> dict[NodeID, tuple[float, float]]:
        new_node_positions: dict[NodeID, tuple[float, float]] = {}

        for node_id, node_position in node_positions.items():
            x, y = node_positions[node_id]
            connected_nodes = node_connected_nodes[node_id]

            if not connected_nodes:
                new_node_positions[node_id] = node_positions[node_id]
                continue

            connected_node_positions = [node_positions[connected_node_id] for connected_node_id in connected_nodes]
            xs, ys = zip(*connected_node_positions)
            new_x, new_y = (sum(xs) / len(xs), sum(ys) / len(ys))
            new_node_positions[node_id] = (x * 0.5 + new_x * 0.5, y * 0.5 + new_y * 0.5)

        return new_node_positions

    score = get_score(node_positions)
    print(f"Score: {score}")

    for j in range(10000):
        if j % 100 == 0:
            print(f"Iteration {j}")

        node_id = list(node_positions.keys())[rnd.randint(0, len(node_positions) - 1)]

        closer_node_positions = move_closer_to_connected(node_positions)
        new_node_positions = node_positions | {node_id: closer_node_positions[node_id]}

        xs, ys = zip(*node_positions.values())

        new_score = get_score(new_node_positions)

        if new_score < score:
            print(f"\tNew score: {new_score}")
            score = new_score
