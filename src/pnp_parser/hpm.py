from collections import defaultdict
from enum import Enum
from typing import Any, Iterable, Sequence
from typing_extensions import TypeIs

from pipeline_manager.dataflow_builder.dataflow_graph import DataflowGraph
from pipeline_manager.dataflow_builder.entities import Interface, Node
from pipeline_manager.specification_builder import SpecificationBuilder
from pydantic import BaseModel

from .fru_model import (
    Bus,
    BusWithSegments,
    Buses,
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


def add_connector_node(
    connector: Connector,
    category: str,
    physical_signals: defaultdict[str, list[str]],
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    spec_builder: SpecificationBuilder,
) -> None:
    if isinstance(connector, ConnectorsMemorySubsystem):
        return

    identifier = connector.identifier.root

    spec_builder.add_node_type(name=identifier, category=category)

    if not isinstance(connector, ConnectorsComposite):
        connected_buses = connector.connected_buses
        if connected_buses:
            for bus in connected_buses.root:
                if not bus.type:
                    continue

                spec_builder.add_node_type_interface(
                    name=identifier, interfacename=bus.identifier, interfacetype=bus.type.lower()
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
    spec_builder: SpecificationBuilder,
) -> None:
    for field in Connectors.model_fields:
        connector_list = getattr(connectors, field)

        if not is_connector_list(connector_list):
            continue

        for connector in connector_list:
            category = connector_categories[field]
            add_connector_node(connector, category, physical_signals, nodes, buses, spec_builder)

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
    spec_builder.add_node_type(name=segment_name, category=f"{bus_category}/Segments/{segment_name}")

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
    spec_builder.add_node_type(name=hub_name, category=f"{bus_category}/Hubs/{hub_name}")

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
    spec_builder.add_node_type(name=mux_name, category=f"{bus_category}/MUXes/{mux_name}")

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

    physical_signals = get_physical_signals(devices, connectors)

    add_device_nodes(devices, physical_signals, nodes, specification_builder)
    add_connector_nodes(connectors, physical_signals, nodes, buses, specification_builder)

    add_bus_nodes(get_buses(hpm), nodes, specification_builder)


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
        if not isinstance(bus, BusWithSegments):
            continue

        bus_name = bus.identifier.root
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
