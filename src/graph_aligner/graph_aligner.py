import typer
import json
from pathlib import Path


app = typer.Typer(pretty_exceptions_show_locals=False)


@app.command()
def read(graph_path: str, position_json_path: str) -> None:
    graph = Path(graph_path)
    if not graph.exists():
        print(f"File not found. Aborting!\n{str(graph)}")
        return

    with open(graph) as f:
        graph_data = json.load(f)
    position_data: dict = {}
    top_graph = graph_data["graphs"][0]
    for node in top_graph["nodes"]:
        node_name = node["name"]
        new_entry = node["position"]
        position_data.update({node_name: new_entry})

    with open(position_json_path, "w") as f:
        json.dump(position_data, f, sort_keys=True, indent=4)


@app.command()
def write(position_json_path: str, graph_path: str) -> None:
    position_json = Path(position_json_path)
    if not position_json.exists():
        print(f"File not found. Aborting!\n{str(position_json)}")
        return
    with open(position_json) as f:
        position_data = json.load(f)

    graph_data = Path(graph_path)
    if not graph_data.exists():
        print(f"File not found. Aborting!\n{str(graph_data)}")
        return
    with open(graph_data) as f:
        graph = json.load(f)

    graph_nodes = graph["graphs"][0]["nodes"]
    for node_name in position_data:
        position = position_data[node_name]
        graph_node = [node for node in graph_nodes if node["name"] == node_name][0]
        graph_node.update({"position": position})

    with open(graph_data, "w") as f:
        json.dump(graph, f, sort_keys=True, indent=4)


if __name__ == "__main__":
    app()
