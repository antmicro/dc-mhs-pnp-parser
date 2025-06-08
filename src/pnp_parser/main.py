import typer
import json
from pathlib import Path

from pipeline_manager.specification_builder import SpecificationBuilder
from pipeline_manager.frontend_builder import build_prepare
from pipeline_manager.dataflow_builder.dataflow_builder import GraphBuilder
from pipeline_manager.dataflow_builder.entities import Node
from pipeline_manager.dataflow_builder.dataflow_graph import DataflowGraph
from pipeline_manager.dataflow_builder.dataflow_graph import AttributeType
from .fru_model import FRU
from .hpm import add_hpm_nodes_to_spec
from .buses import add_buses_nodes_to_spec


app = typer.Typer(pretty_exceptions_show_locals=False)
# app = typer.Typer()

SPECIFICATION_VERSION = "20240723.13"
specification_builder = SpecificationBuilder(spec_version=SPECIFICATION_VERSION)


def create_spec(fru: FRU, buses: dict, output_spec: str, workspace: Path) -> SpecificationBuilder:
    specification_builder.metadata_add_param(paramname="connectionStyle", paramvalue="orthogonal")
    specification_builder.metadata_add_param(paramname="twoColumn", paramvalue=True)
    specification_builder.metadata_add_param(paramname="layout", paramvalue="CytoscapeEngine - grid")


    add_hpm_nodes_to_spec(fru.HPM.Connectors, buses, specification_builder)
    add_buses_nodes_to_spec(fru.Buses, buses, specification_builder)

    specification = specification_builder.create_and_validate_spec(
        dump_spec="dump.json", sort_spec=True, workspacedir=str(workspace)
    )
    with open(output_spec, "w") as f:
        json.dump(specification, f, sort_keys=True, indent=4)
    return specification


def get_interface_from_node(nodes: dict, graph: GraphBuilder, device_data: tuple[str, str]) -> AttributeType.INTERFACE:
    node = nodes[device_data[0]]
    graph.get(AttributeType.INTERFACE, name=device_data[1])
    return node.get(AttributeType.INTERFACE, name=device_data[1])[0]


def create_graph(fru: FRU, buses: dict, output_spec: str, graph_name: str, workspace: Path) -> None:
    builder = GraphBuilder(
        specification=output_spec, specification_version=specification_builder.version, workspace_directory=workspace
    )
    graph = builder.create_graph()
    nodes: dict = {}
    for node in output_spec["nodes"]:
        nodes.update({node["name"]: graph.create_node(name=node["name"])})

    # print(buses)
    for bus in buses:
        devices = buses[bus]
        if len(devices) < 2:
            continue
        first_interface = get_interface_from_node(nodes, graph, devices[0])
        for device in devices[1:]:
            next_interface = get_interface_from_node(nodes, graph, device)
            graph.create_connection(first_interface, next_interface)
    builder.save(graph_name)


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
    spec = create_spec(fru, buses, output_spec, workspace)
    create_graph(fru, buses, spec, output_graph, workspace)


if __name__ == "__main__":
    app()
