from pipeline_manager.specification_builder import SpecificationBuilder, SpecificationBuilderException

from typing import List
from .fru_model import Buses


def add_buses_nodes_to_spec(fru_buses: Buses, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
    for bus_name, bus_body in fru_buses:
        if hasattr(bus_body[0], "Trees"):
            if hasattr(bus_body[0].Trees[0], "Devices"):
                for device in bus_body[0].Trees[0].Devices:
                    builder.add_node_type(name=device.Identifier, category=f"Devices/{bus_name}")
                    builder.add_node_type_interface(
                        name=device.Identifier, interfacename=bus_name, interfacetype=bus_name.lower()
                    )
                    if hasattr(device, "Manufacturers"):
                        builder.add_node_type_property(
                            name=device.Identifier,
                            propname="Vendor",
                            proptype="constant",
                            default=device.Manufacturers[0],
                        )
                    if hasattr(device, "Models"):
                        builder.add_node_type_property(
                            name=device.Identifier, propname="Model", proptype="constant", default=device.Models[0]
                        )
                    if hasattr(device, "Address"):
                        builder.add_node_type_property(
                            name=device.Identifier, propname="Address", proptype="constant", default=device.Address
                        )
                    buses.setdefault(bus_body[0].Identifier, []).append([device.Identifier, bus_name])
                    nodes.append(device.Identifier)
        if hasattr(bus_body[0], "ConnectedDevices"):
            for connected_device in bus_body[0].ConnectedDevices:
                try:
                    builder.add_node_type(name=connected_device.Endpoint, category=f"Devices/{bus_name}")
                except SpecificationBuilderException:
                    pass

                try:
                    builder.add_node_type_interface(
                        name=connected_device.Endpoint, interfacename=bus_name, interfacetype=bus_name.lower()
                    )
                except SpecificationBuilderException:
                    pass
                buses.setdefault(bus_body[0].Identifier, []).append([connected_device.Endpoint, bus_name])
                nodes.append(connected_device.Endpoint)
