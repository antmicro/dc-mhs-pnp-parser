from enum import Enum
from typing import Any

from pipeline_manager.specification_builder import SpecificationBuilder

from .fru_model import HardwareComponent, Connectors


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

    for attr, attr_field_info in type(connector).model_fields.items():
        attr_value = getattr_none(connector, attr)

        valid_attr_value = isinstance(attr_value, (int, str, bool, Enum))
        if not valid_attr_value:
            continue

        if isinstance(attr_value, Enum):
            attr_value = attr_value.value

        spec_builder.add_node_type_property(
            name=identifier,
            propname=attr_field_info.alias or attr,
            proptype="constant",
            default=str(attr_value),
        )

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


def add_hpm_nodes_to_spec(
    hpm: HardwareComponent,
    nodes: list[str],
    buses: dict[str, list[tuple[str, str]]],
    specification_builder: SpecificationBuilder,
) -> None:
    connectors = hpm.component.connectors
    add_connector_nodes(connectors, nodes, buses, specification_builder)
