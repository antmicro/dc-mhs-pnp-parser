from itertools import combinations
from enum import Enum
from typing import Any

from pipeline_manager.dataflow_builder.dataflow_graph import DataflowGraph
from pipeline_manager.dataflow_builder.entities import Interface, Node
from pipeline_manager.specification_builder import SpecificationBuilder
from pydantic import BaseModel

from .fru_model import BusesI2C, HardwareComponent, Connectors, Devices, MuX, Segment, Slot


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


def add_i2c_mux(
    mux: MuX,
    input_segment_name: str,
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    mux_name = mux.identifier.root
    spec_builder.add_node_type(name=mux_name, category=f"MUXes/{mux_name}")

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


def add_i2c_muxes(
    i2c_buses: list[BusesI2C],
    nodes: list[str],
    spec_builder: SpecificationBuilder,
) -> None:
    for bus in i2c_buses:
        for segment in bus.segments:
            input_segment_name = segment.identifier.root

            for mux in segment.muxes or []:
                add_i2c_mux(mux, input_segment_name, nodes, spec_builder)


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

    i2c_buses = hpm.component.buses.i2c or []
    add_i2c_muxes(i2c_buses, nodes, specification_builder)


def connect_i2c_segment_connectors(
    i2c_bus_name: str,
    i2c_segment: Segment,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i2c_segment.connectors:
        return

    connectors = i2c_segment.connectors.root
    for connector1, connector2 in combinations(connectors, 2):
        connector1_node = graph_nodes[connector1.endpoint]
        connector2_node = graph_nodes[connector2.endpoint]

        [connector1_interface] = connector1_node.get_interfaces_by_regex(i2c_bus_name)
        [connector2_interface] = connector2_node.get_interfaces_by_regex(i2c_bus_name)

        hpm_graph.create_connection(connector1_interface, connector2_interface)


def connect_i2c_segment_muxes(
    i2c_segment: Segment,
    segment_interfaces: dict[str, list[Interface]],
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    if not i2c_segment.muxes:
        return

    for mux in i2c_segment.muxes:
        mux_name = mux.identifier.root
        mux_node = graph_nodes[mux_name]

        input_segment = i2c_segment.identifier.root
        [mux_input_interface] = mux_node.get_interfaces_by_regex(input_segment)

        for input_segment_interface in segment_interfaces[input_segment]:
            hpm_graph.create_connection(input_segment_interface, mux_input_interface)

        for channel in mux.channels:
            output_segment = channel.endpoint.root
            [mux_output_interface] = mux_node.get_interfaces_by_regex(output_segment)

            for output_segment_interface in segment_interfaces[output_segment]:
                hpm_graph.create_connection(mux_output_interface, output_segment_interface)


def get_i2c_interfaces(i2c_bus_name: str, i2c_segment: Segment, graph_nodes: dict[str, Node]) -> list[Interface]:
    if not i2c_segment.connectors:
        return []

    connectors = i2c_segment.connectors.root
    connector_interfaces = []

    for connector in connectors:
        connector_node = graph_nodes[connector.endpoint]
        [connector_interface] = connector_node.get_interfaces_by_regex(i2c_bus_name)
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
            connect_i2c_segment_muxes(segment, segment_interfaces, hpm_graph, graph_nodes)


def add_hpm_graph_connections(
    hpm: HardwareComponent,
    hpm_graph: DataflowGraph,
    graph_nodes: dict[str, Node],
) -> None:
    buses = hpm.component.buses
    if not buses:
        return

    add_i2c_bus_connections(buses.i2c or [], hpm_graph, graph_nodes)
