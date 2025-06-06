import typer
import json
from pathlib import Path

from pipeline_manager.specification_builder import SpecificationBuilder
from pipeline_manager.frontend_builder import build_prepare
from pipeline_manager.dataflow_builder.dataflow_builder import GraphBuilder
from pipeline_manager.dataflow_builder.entities import Node
from pipeline_manager.dataflow_builder.dataflow_graph import DataflowGraph
from .fru_model import FRU
from .fru_classes import (
    Soc,
    MemorySubsystem,
    Composite,
    Mxio,
    Mpic,
    PowerSupply,
    OCPMezzanineSlot,
    ControlPanel,
    Sci,
    Fan,
    RtcBattery,
    PDB,
    specification_builder,
)


app = typer.Typer(pretty_exceptions_show_locals=False)
# app = typer.Typer()


def add_node(fru: FRU, prop: str, class_name: type, specification_builder: SpecificationBuilder) -> None:
    node_data = getattr(fru.HPM.Connectors, prop)[0].model_dump()
    node = class_name(**node_data)
    node.to_spec_node(specification_builder)


def create_spec(fru: FRU, output_spec: str, workspace: Path) -> SpecificationBuilder:
    add_node(fru, "SOCs", Soc, specification_builder)
    add_node(fru, "MemorySubsystems", MemorySubsystem, specification_builder)
    add_node(fru, "Composites", Composite, specification_builder)
    add_node(fru, "Mxios", Mxio, specification_builder)
    add_node(fru, "Mpics", Mpic, specification_builder)
    add_node(fru, "PowerSupplies", PowerSupply, specification_builder)
    add_node(fru, "OCPMezzanineSlots", OCPMezzanineSlot, specification_builder)
    add_node(fru, "ControlPanels", ControlPanel, specification_builder)
    add_node(fru, "SCIs", Sci, specification_builder)
    add_node(fru, "Fans", Fan, specification_builder)
    add_node(fru, "RealTimeClockBatteries", RtcBattery, specification_builder)
    add_node(fru, "PowerDistributionBoards", PDB, specification_builder)

    specification_builder.metadata_add_param(paramname="connectionStyle", paramvalue="orthogonal")
    specification_builder.metadata_add_param(paramname="twoColumn", paramvalue=True)

    specification = specification_builder.create_and_validate_spec(
        dump_spec="dump.json", sort_spec=True, workspacedir=str(workspace)
    )
    with open(output_spec, "w") as f:
        json.dump(specification, f, sort_keys=True, indent=4)
    return specification


def create_graph(fru: FRU, output_spec: str, graph_name: str, workspace: Path) -> None:
    builder = GraphBuilder(
        specification=output_spec, specification_version=specification_builder.version, workspace_directory=workspace
    )
    graph = builder.create_graph()
    for node in output_spec["nodes"]:
        graph.create_node(name=node["name"])

    buses: dict = dict()
    for conn in fru.HPM.Connectors:
        print(conn[0])
        for bus in getattr(conn, "ConnectedBuses"):
            buses[bus["Identifier"]].append(conn["Identifier"])
    print(buses)
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

    spec = create_spec(fru, output_spec, workspace)
    create_graph(fru, spec, output_graph, workspace)


if __name__ == "__main__":
    app()
