from .fru_model import FRU, FPGA
from .fru_model import IPBlock as IPBlockBase, VirtualWire as VirtualWireBase
from pipeline_manager.specification_builder import SpecificationBuilder
from pipeline_manager.dataflow_builder.dataflow_builder import DataflowGraph
from pipeline_manager.dataflow_builder.dataflow_graph import AttributeType

from typing import List


class IPBlock(IPBlockBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        node_name = self.Identifier
        interface_type = self.Type.upper()
        interface_identifier = f"{interface_type}-0"
        builder.add_node_type(
            name=node_name,
            category="FPGA/IPBlocks",
        )
        builder.add_node_type_interface(name=node_name, interfacename=interface_type, interfacetype=self.Type)
        buses.setdefault(interface_identifier, []).append([node_name, interface_type])
        nodes.append(node_name)


class VirtualWire(VirtualWireBase):
    def to_spec_node(self, buses: dict, nodes: List[str], builder: SpecificationBuilder) -> None:
        node_name = self.Identifier
        builder.add_node_type(
            name=node_name,
            category="FPGA/VirtualWires",
        )
        builder.add_node_type_property(name=node_name, propname="Alias", proptype="constant", default=self.Alias)
        for interface in self.MappedInterfaces:
            # hardcoded correction for faulty input data (it is against spec)
            interface_name = "LTPI-0" if interface.Mapping == "LTPI-1-0" else interface.Mapping
            builder.add_node_type_interface(
                name=node_name, interfacename=interface.Identifier, interfacetype=interface.Interface.lower()
            )
            # buses.setdefault(interface.Identifier, []).append([node_name, interface_map])
            buses.setdefault(interface_name, []).append([node_name, interface.Interface.lower()])
        nodes.append(node_name)


class Fpga(FPGA):
    node_name: str = ""

    def to_spec_node(self, fpga_buses: dict, buses: dict, builder: SpecificationBuilder) -> None:
        # self.node_name = f"{self.Manufacturer}-{self.Model}"
        self.node_name = "FPGA"
        builder.add_node_type(
            name=self.node_name,
            category="FPGA",
        )
        builder.add_node_type_property(
            name=self.node_name, propname="Build Version", proptype="constant", default=self.Build.Version
        )
        builder.add_node_type_property(
            name=self.node_name, propname="BuildTimestamp", proptype="constant", default=self.Build.BuildTimestamp
        )
        builder.add_node_type_property(name=self.node_name, propname="Model", proptype="constant", default=self.Model)
        builder.add_node_type_property(
            name=self.node_name, propname="Manufacturer", proptype="constant", default=self.Manufacturer
        )
        added_interfaces: list = []
        for bus_name in fpga_buses:
            bus = fpga_buses[bus_name][0]
            if bus[1] not in added_interfaces:
                added_interfaces.append(bus[1])
                builder.add_node_type_interface(name=self.node_name, interfacename=bus[1], interfacetype=bus[1].lower())
                buses.setdefault(bus_name, []).append([self.node_name, bus[1]])


def add_nodes(
    fru: FRU, prop: str, class_name: type, buses: dict, nodes: List[str], specification_builder: SpecificationBuilder
) -> None:
    nodes_data = getattr(fru, prop)
    for node_data in nodes_data:
        node = class_name(**node_data.model_dump())
        node.to_spec_node(buses, nodes, specification_builder)


def add_fpga_nodes_to_spec(
    fru: FRU, buses: dict, nodes: List[str], specification_builder: SpecificationBuilder
) -> dict:
    fpga_buses: dict = {}
    add_nodes(fru.FPGA, "IPBlocks", IPBlock, fpga_buses, nodes, specification_builder)
    # add_nodes(fru.FPGA, "VirtualWires", VirtualWire, fpga_buses, nodes, specification_builder)

    fpga_node_data = fru.FPGA.model_dump()
    fpga_node = Fpga(**fpga_node_data)
    fpga_node.to_spec_node(fpga_buses, buses, specification_builder)

    return fpga_buses
