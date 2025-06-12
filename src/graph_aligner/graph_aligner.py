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


if __name__ == "__main__":
    app()
