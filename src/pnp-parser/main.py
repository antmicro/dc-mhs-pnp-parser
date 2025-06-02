import typer
import json


app = typer.Typer()

@app.command()
def main(fru_json: str):
    with open(fru_json) as f:
        print(json.load(f))

if __name__ == "__main__":
    app()
