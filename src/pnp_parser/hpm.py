from enum import Enum
from typing import Any, Sequence
from typing_extensions import TypeIs

from pipeline_manager.dataflow_builder.dataflow_graph import DataflowGraph
from pipeline_manager.dataflow_builder.entities import Interface, Node
from pipeline_manager.specification_builder import SpecificationBuilder
from pydantic import BaseModel

from .fru_model import (
    Bus,
    Buses,
    BusesI2C,
    BusesI3C,
    BusesJTAG,
    BusesNCSIRBT,
    BusesUART,
    BusesUSB,
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
    Segment,
    SegmentI2C,
    SegmentI3C,
    SegmentJTAG,
    SegmentNCSIRBT,
    SegmentUART,
    SegmentUSB,
    Slot,
)


segment_categories: dict[type[Segment], str] = {
    SegmentI2C: "I2C",
    SegmentI3C: "I3C",
    SegmentJTAG: "JTAG",
    SegmentUSB: "USB",
    SegmentNCSIRBT: "NC-SI RBT",
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


def getattr_none(o: Any, name: str) -> Any | None:
    return getattr(o, name) if hasattr(o, name) else None


def set_node_attributes(model: BaseModel, node_name: str, spec_builder: SpecificationBuilder):
    for attr, attr_field_info in type(model).model_fields.items():
        attr_value = getattr_none(model, attr)

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
    connector: Any,
    category: str,
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    spec_builder: SpecificationBuilder,
) -> None:
    identifier = connector.identifier.root

    spec_builder.add_node_type(name=identifier, category=category)

    connected_buses = getattr_none(connector, "connected_buses")
    if connected_buses:
        for bus in connected_buses.root:
            if not bus.type:
                continue

            spec_builder.add_node_type_interface(
                name=identifier, interfacename=bus.identifier, interfacetype=bus.type.lower()
            )
            buses.setdefault(bus.identifier, []).append((identifier, bus.type))

    set_node_attributes(connector, identifier, spec_builder)

    nodes.append(identifier)


def add_memory_subsystem_slot_node(slot: Slot, nodes: list[str], spec_builder: SpecificationBuilder) -> None:
    identifier = slot.identifier.root

    spec_builder.add_node_type(name=identifier, category="Connectors/DIMM Slots")

    connected_buses = getattr_none(slot, "connected_buses")
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
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    spec_builder: SpecificationBuilder,
) -> None:
    for field in Connectors.model_fields:
        connector_list = getattr(connectors, field)

        connector_list_valid = type(connector_list) is list and hasattr(connector_list[0], "identifier")
        if not connector_list_valid:
            continue

        for connector in connector_list:
            category = connector_categories[field]
            add_connector_node(connector, category, nodes, buses, spec_builder)

    for memory_subsystem in connectors.memory_subsystems or []:
        for slot in memory_subsystem.slots:
            add_memory_subsystem_slot_node(slot, nodes, spec_builder)


def add_device_nodes(
    devices: Devices,
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    for device in devices.root:
        node_name = device.identifier.root

        if not device.type:
            continue

        spec_builder.add_node_type(name=node_name, category=f"Devices/{device.type}")

        if device.connected_buses:
            for connected_bus in device.connected_buses.root:
                if not connected_bus.type:
                    continue

                spec_builder.add_node_type_interface(
                    name=node_name, interfacename=connected_bus.identifier, interfacetype=connected_bus.type.lower()
                )

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


def add_i2c_segment(
    i2c_bus_name: str,
    segment: SegmentI2C,
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    segment_name = segment.identifier.root
    spec_builder.add_node_type(name=segment_name, category=f"I2C/Segments/{segment_name}")

    set_node_attributes(segment, segment_name, spec_builder)

    spec_builder.add_node_type_interface(
        name=segment_name, interfacename=segment_name, interfacetype="i2c", side="right", maxcount=-1
    )

    nodes.append(segment_name)


def add_i2c_mux(
    mux: MuXI2C,
    input_segment_name: str,
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    mux_name = mux.identifier.root
    spec_builder.add_node_type(name=mux_name, category=f"I2C/MUXes/{mux_name}")

    set_node_attributes(mux, mux_name, spec_builder)

    spec_builder.add_node_type_property(
        name=mux_name, propname="Manufacturer", proptype="constant", default=mux.manufacturers.root[0]
    )

    if mux.models:
        spec_builder.add_node_type_property(
            name=mux_name, propname="Model", proptype="constant", default=mux.models.root[0]
        )

    spec_builder.add_node_type_interface(
        name=mux_name, interfacename=input_segment_name, interfacetype="i2c", side="left"
    )

    for channel in mux.channels:
        output_segment_name = channel.endpoint.root
        spec_builder.add_node_type_interface(
            name=mux_name, interfacename=output_segment_name, interfacetype="i2c", side="right"
        )

    nodes.append(mux_name)


def add_i2c_nodes(
    i2c_buses: list[BusesI2C],
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    for bus in i2c_buses:
        i2c_bus_name = bus.identifier.root

        for segment in bus.segments:
            input_segment_name = segment.identifier.root

            add_i2c_segment(i2c_bus_name, segment, nodes, spec_builder)

            for mux in segment.muxes or []:
                add_i2c_mux(mux, input_segment_name, nodes, spec_builder)


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
        i3c_bus_name = bus.identifier.root

        if isinstance(bus, (BusesI2C, BusesI3C, BusesJTAG, BusesUSB, BusesNCSIRBT, BusesUART)):
            for segment in bus.segments:
                input_segment_name = segment.identifier.root
                add_segment(segment, nodes, spec_builder)

                if isinstance(segment, (SegmentI3C, SegmentUSB)):
                    for hub in segment.hubs or []:
                        add_hub(hub, input_segment_name, nodes, spec_builder)

                if isinstance(segment, (SegmentI2C, SegmentI3C, SegmentJTAG, SegmentUSB, SegmentUART)):
                    for mux in segment.muxes or []:
                        add_mux(mux, input_segment_name, nodes, spec_builder)


def is_bus_list(x: Any) -> TypeIs[list[Bus]]:
    return isinstance(x, list) and all(isinstance(x_elem, Bus) for x_elem in x)


def add_hpm_nodes_to_spec(
    hpm: HardwareComponent,
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    specification_builder: SpecificationBuilder,
) -> None:
    connectors = hpm.component.connectors
    add_connector_nodes(connectors, nodes, buses, specification_builder)

    devices = hpm.component.devices
    add_device_nodes(devices, nodes, specification_builder)

    all_buses_list: list[Bus] = []

    for bus_list_name in Buses.model_fields:
        field_value = getattr(hpm.component.buses, bus_list_name)

        if is_bus_list(field_value):
            all_buses_list.extend(field_value)

    add_bus_nodes(all_buses_list, nodes, specification_builder)


def connect_i2c_segment_connectors(
    i2c_bus_name: str,
    i2c_segment: SegmentI2C,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i2c_segment.connectors:
        return

    segment_node = graph_nodes[i2c_segment.identifier.root]
    [segment_interface] = segment_node.get_interfaces_by_regex(f"{i2c_bus_name}")

    connectors = i2c_segment.connectors.root
    for connector in connectors:
        connector_node = graph_nodes[connector.endpoint]
        [connector_interface] = connector_node.get_interfaces_by_regex(i2c_bus_name)

        hpm_graph.create_connection(connector_interface, segment_interface)


def connect_i2c_segment_devices(
    i2c_bus_name: str,
    i2c_segment: SegmentI2C,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i2c_segment.connected_devices:
        return

    segment_node = graph_nodes[i2c_segment.identifier.root]
    [segment_interface] = segment_node.get_interfaces_by_regex(f"{i2c_bus_name}")

    devices = i2c_segment.connected_devices.root
    for device in devices:
        device_node = graph_nodes[device.endpoint]
        [device_interface] = device_node.get_interfaces_by_regex(i2c_bus_name)

        hpm_graph.create_connection(device_interface, segment_interface)


def connect_i2c_segment_muxes(
    i2c_segment: SegmentI2C,
    segment_interfaces: dict[str, list[Interface]],
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i2c_segment.muxes:
        return

    input_segment_name = i2c_segment.identifier.root
    input_segment_node = graph_nodes[input_segment_name]
    [input_segment_interface] = input_segment_node.get_interfaces_by_regex(input_segment_name)

    for mux in i2c_segment.muxes:
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


def connect_i3c_segment_connectors(
    i3c_bus_name: str,
    i3c_segment: SegmentI3C,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i3c_segment.connectors:
        return

    segment_node = graph_nodes[i3c_segment.identifier.root]
    [segment_interface] = segment_node.get_interfaces_by_regex(f"{i3c_bus_name}")

    connectors = i3c_segment.connectors.root
    for connector in connectors:
        connector_node = graph_nodes[connector.endpoint]
        [connector_interface] = connector_node.get_interfaces_by_regex(i3c_bus_name)

        hpm_graph.create_connection(connector_interface, segment_interface)


def connect_i3c_segment_devices(
    i3c_bus_name: str,
    i3c_segment: SegmentI3C,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i3c_segment.connected_devices:
        return

    segment_node = graph_nodes[i3c_segment.identifier.root]
    [segment_interface] = segment_node.get_interfaces_by_regex(f"{i3c_bus_name}")

    devices = i3c_segment.connected_devices.root
    for device in devices:
        device_node = graph_nodes[device.endpoint]
        [device_interface] = device_node.get_interfaces_by_regex(i3c_bus_name)

        hpm_graph.create_connection(device_interface, segment_interface)


def connect_i3c_segment_muxes(
    i3c_segment: SegmentI3C,
    segment_interfaces: dict[str, list[Interface]],
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i3c_segment.muxes:
        return

    input_segment_name = i3c_segment.identifier.root
    input_segment_node = graph_nodes[input_segment_name]
    [input_segment_interface] = input_segment_node.get_interfaces_by_regex(input_segment_name)

    for mux in i3c_segment.muxes:
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


def connect_i3c_segment_hubs(
    i3c_segment: SegmentI3C,
    segment_interfaces: dict[str, list[Interface]],
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i3c_segment.hubs:
        return

    input_segment_name = i3c_segment.identifier.root
    input_segment_node = graph_nodes[input_segment_name]
    [input_segment_interface] = input_segment_node.get_interfaces_by_regex(input_segment_name)

    for hub in i3c_segment.hubs:
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


def get_i2c_interfaces(i2c_bus_name: str, i2c_segment: SegmentI2C, graph_nodes: dict[str, Node]) -> list[Interface]:
    if not i2c_segment.connectors:
        return []

    connectors = i2c_segment.connectors.root
    connector_interfaces = []

    for connector in connectors:
        connector_node = graph_nodes[connector.endpoint]
        [connector_interface] = connector_node.get_interfaces_by_regex(i2c_bus_name)
        connector_interfaces.append(connector_interface)

    return connector_interfaces


def get_i3c_interfaces(i3c_bus_name: str, i3c_segment: SegmentI3C, graph_nodes: dict[str, Node]) -> list[Interface]:
    if not i3c_segment.connectors:
        return []

    connectors = i3c_segment.connectors.root
    connector_interfaces = []

    for connector in connectors:
        connector_node = graph_nodes[connector.endpoint]
        [connector_interface] = connector_node.get_interfaces_by_regex(i3c_bus_name)
        connector_interfaces.append(connector_interface)

    return connector_interfaces


def add_i2c_bus_connections(
    i2c_buses: list[BusesI2C],
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    for bus in i2c_buses:
        i2c_bus_name = bus.identifier.root
        segment_interfaces: dict[str, list[Interface]] = {
            segment.identifier.root: get_i2c_interfaces(i2c_bus_name, segment, graph_nodes)  #
            for segment in bus.segments
        }

        for segment in bus.segments:
            connect_i2c_segment_connectors(i2c_bus_name, segment, hpm_graph, graph_nodes)
            connect_i2c_segment_devices(i2c_bus_name, segment, hpm_graph, graph_nodes)
            connect_i2c_segment_muxes(segment, segment_interfaces, hpm_graph, graph_nodes)


def add_i3c_bus_connections(
    i3c_buses: list[BusesI3C],
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    for bus in i3c_buses:
        i3c_bus_name = bus.identifier.root
        segment_interfaces: dict[str, list[Interface]] = {
            segment.identifier.root: get_i3c_interfaces(i3c_bus_name, segment, graph_nodes)  #
            for segment in bus.segments
        }

        for segment in bus.segments:
            connect_i3c_segment_connectors(i3c_bus_name, segment, hpm_graph, graph_nodes)
            connect_i3c_segment_devices(i3c_bus_name, segment, hpm_graph, graph_nodes)
            connect_i3c_segment_muxes(segment, segment_interfaces, hpm_graph, graph_nodes)
            connect_i3c_segment_hubs(segment, segment_interfaces, hpm_graph, graph_nodes)


def add_hpm_graph_connections(
    hpm: HardwareComponent,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    buses = hpm.component.buses
    if not buses:
        return

    add_i2c_bus_connections(buses.i2c or [], hpm_graph, graph_nodes)
    add_i3c_bus_connections(buses.i3c or [], hpm_graph, graph_nodes)
