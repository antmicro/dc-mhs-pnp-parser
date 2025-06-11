import typer
import json
from pathlib import Path
from pipeline_manager.specification_builder import SpecificationBuilder
from pipeline_manager.frontend_builder import build_prepare
from pipeline_manager.dataflow_builder.dataflow_builder import GraphBuilder, DataflowGraph
from pipeline_manager.dataflow_builder.dataflow_graph import AttributeType
from .fru_model import FRU
from .hpm import add_hpm_nodes_to_spec
from .buses import add_buses_nodes_to_spec
from .fpga import add_fpga_nodes_to_spec
from typing import List
import copy

app = typer.Typer(pretty_exceptions_show_locals=False)
# app = typer.Typer()

SPECIFICATION_VERSION = "20240723.13"
specification_builder = SpecificationBuilder(spec_version=SPECIFICATION_VERSION)


def create_spec(fru: FRU, buses: dict, workspace: Path) -> SpecificationBuilder:
    specification_builder.metadata_add_param(paramname="connectionStyle", paramvalue="orthogonal")
    specification_builder.metadata_add_param(paramname="twoColumn", paramvalue=True)
    specification_builder.metadata_add_param(paramname="layout", paramvalue="CytoscapeEngine - grid")

    hpm_nodes: List[str] = []
    fpga_nodes: List[str] = []
    buses_nodes: List[str] = []
    add_hpm_nodes_to_spec(fru.HPM.Connectors, buses, hpm_nodes, specification_builder)
    add_buses_nodes_to_spec(fru.Buses, buses, buses_nodes, specification_builder)
    fpga_buses: dict = add_fpga_nodes_to_spec(fru, buses, fpga_nodes, specification_builder)
    specification = specification_builder.create_and_validate_spec(
        dump_spec="dump.json", sort_spec=True, workspacedir=str(workspace)
    )
    return [specification, fpga_buses, hpm_nodes, fpga_nodes, buses_nodes]


def create_graph(
    graph_builder: GraphBuilder, graph_nodes_names: List[str], nodes: dict, subgraph: bool = False
) -> DataflowGraph:
    graph = graph_builder.create_graph()
    for node_name in graph_nodes_names:
        new_node = graph.create_node(name=node_name)
        nodes.update({node_name: new_node})
    return graph


def get_interface_from_node(nodes: dict, graph: GraphBuilder, device_data: tuple[str, str]) -> AttributeType.INTERFACE:
    if device_data[0] not in nodes:
        return None
    node = nodes[device_data[0]]
    graph.get(AttributeType.INTERFACE, name=device_data[1])
    nodes = node.get(AttributeType.INTERFACE, name=device_data[1])
    if nodes:
        return nodes[0]
    return None


def make_graph_connections(graph: DataflowGraph, buses: dict, nodes: dict) -> DataflowGraph:
    for bus in buses:
        devices = buses[bus]
        if len(devices) < 2:
            continue
        first_interface = get_interface_from_node(nodes, graph, devices[0])
        for device in devices[1:]:
            next_interface = get_interface_from_node(nodes, graph, device)
            if next_interface:
                graph.create_connection(first_interface, next_interface)
    return graph


def merge_buses(bus1: dict, bus2: dict) -> dict:
    for bus in bus2.keys():
        if bus in bus1:
            for entry in bus2[bus]:
                bus1[bus].append(entry)
        else:
            bus1.update({bus: bus2[bus]})
    return bus1


@app.command()
def main(fru_json: str, output_spec: str, output_graph: str) -> None:
    with open(fru_json) as f:
        hpm_data = json.load(f)
    fru = FRU.model_validate(hpm_data)

    workspace = Path("workspace")
    if workspace.exists():
        build_prepare(workspace, skip_install_deps=True)
    else:
        build_prepare(workspace)
    buses: dict = {}
    print("Creating spec..")
    [spec, fpga_buses, hpm_nodes, fpga_nodes_names, buses_nodes] = create_spec(fru, buses, workspace)
    graph_builder = GraphBuilder(
        specification=spec, specification_version=specification_builder.version, workspace_directory=workspace
    )
    top_graph_nodes_names = hpm_nodes
    top_graph_nodes_names.extend(buses_nodes)
    top_graph_nodes_names = list(dict.fromkeys(top_graph_nodes_names))
    top_graph_nodes: dict = {}
    print("Creating HPM graph..")
    hpm_graph = create_graph(graph_builder, top_graph_nodes_names, top_graph_nodes)
    fpga_graph_nodes: dict = {}
    print("Creating FPGA graph..")
    fpga_graph = create_graph(graph_builder, fpga_nodes_names, fpga_graph_nodes, subgraph=True)
    hpm_graph.name = "Top Graph"
    fpga_graph.name = "FPGA Graph"

    print("Connecting FPGA graph as subgraph..")
    fpga_node = hpm_graph.create_subgraph_node("FPGA", fpga_graph.id)
    top_graph_nodes.update({fpga_node.name: fpga_node})
    # add subgraph
    fpga_graph_json = fpga_graph.to_json(as_str=False)
    specification_builder.add_subgraph_from_spec(fpga_graph_json)
    specification_builder.add_node_type_subgraph_id(name="FPGA", subgraph_id=fpga_graph_json["id"])
    print("Validating specification..")
    specification = specification_builder.create_and_validate_spec(
        dump_spec="dump.json", sort_spec=True, workspacedir=str(workspace)
    )
    with open(output_spec, "w") as f:
        json.dump(specification, f, sort_keys=True, indent=4)
    for node_name in fpga_graph_nodes:
        node = fpga_graph_nodes[node_name]
        for interface in node.interfaces:
            fpga_node.interfaces.append(copy.copy(interface))
            interface.external_name = interface.name
    print("Add HPM connections..")
    make_graph_connections(hpm_graph, buses, top_graph_nodes)
    print("Add FPGA connections..")
    make_graph_connections(fpga_graph, fpga_buses, fpga_graph_nodes)
    graph_builder.save(output_graph)


if __name__ == "__main__":
    app()
