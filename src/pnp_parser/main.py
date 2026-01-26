from typing import Iterable
from pipeline_manager.dataflow_builder.entities import Node
import typer
import json

from pathlib import Path
from pipeline_manager.specification_builder import SpecificationBuilder
from pipeline_manager.frontend_builder import build_prepare

from pnp_parser.hpm import (
    add_hpm_graph_connections,
    add_hpm_styles_to_spec,
    add_hpm_layers_to_spec,
    add_hpm_nodes_to_spec,
    place_hpm_graph_nodes_fewest_connections,
    place_hpm_graph_nodes_grid,
    place_hpm_graph_nodes_line,
    place_hpm_graph_nodes_tree,
)

from pipeline_manager.dataflow_builder.dataflow_builder import GraphBuilder, DataflowGraph

from .fru_model import HardwareComponent
from dataclasses import dataclass

app = typer.Typer(pretty_exceptions_show_locals=False)

SPECIFICATION_VERSION = "20250623.14"
specification_builder = SpecificationBuilder(spec_version=SPECIFICATION_VERSION)


@dataclass
class FruSpec:
    spec: dict
    hpm_nodes: list[str]
    hpm_buses: dict[str, list[tuple[str, str]]]


def create_spec(hpm: HardwareComponent, workspace: Path) -> FruSpec:
    specification_builder.metadata_add_param(paramname="connectionStyle", paramvalue="orthogonal")
    specification_builder.metadata_add_param(paramname="twoColumn", paramvalue=True)
    specification_builder.metadata_add_param(paramname="layout", paramvalue="CytoscapeEngine - dagre-longest-path")

    hpm_nodes: list[str] = []
    hpm_buses: dict[str, list[tuple[str, str]]] = {}
    add_hpm_styles_to_spec(specification_builder)
    add_hpm_nodes_to_spec(hpm, hpm_nodes, hpm_buses, specification_builder)
    add_hpm_layers_to_spec(specification_builder)

    spec = specification_builder.create_and_validate_spec(
        dump_spec="dump.json", sort_spec=True, workspacedir=str(workspace)
    )
    return FruSpec(spec, hpm_nodes, hpm_buses)


def create_graph(
    graph_builder: GraphBuilder,
    name: str,
    graph_nodes_names: Iterable[str],
    graph_nodes: dict[str, Node],
    subgraph: bool = False,
) -> DataflowGraph:
    graph = graph_builder.create_graph()
    graph.name = name

    for node_name in graph_nodes_names:
        new_node = graph.create_node(name=node_name)
        graph_nodes[node_name] = new_node

    return graph


@app.command()
def main(fru_json: str, output_spec: Path, output_graph: Path) -> None:
    with open(fru_json) as f:
        hpm_data = json.load(f)

    hpm = HardwareComponent.model_validate(hpm_data)

    workspace = Path("workspace")
    if workspace.exists():
        _ = build_prepare(workspace, skip_install_deps=True)
    else:
        _ = build_prepare(workspace)

    fru_spec = create_spec(hpm, workspace)

    graph_builder = GraphBuilder(
        specification=fru_spec.spec, specification_version=specification_builder.version, workspace_directory=workspace
    )

    top_graph_nodes: dict[str, Node] = {}

    print("Creating HPM graph..")
    hpm_graph = create_graph(graph_builder, "Top Graph", set(fru_spec.hpm_nodes), top_graph_nodes)
    add_hpm_graph_connections(hpm, hpm_graph, top_graph_nodes)
    place_hpm_graph_nodes_tree(hpm_graph)

    print("Validating specification..")
    spec = specification_builder.create_and_validate_spec(
        dump_spec="dump.json", sort_spec=True, workspacedir=str(workspace)
    )
    with open(output_spec, "w") as f:
        json.dump(spec, f, sort_keys=True, indent=4)

    graph_builder.save(output_graph)


if __name__ == "__main__":
    app()
