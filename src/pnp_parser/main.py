import typer
import json

from .fru_model import HardwareComponent

app = typer.Typer(pretty_exceptions_show_locals=False)


@app.command()
def main(fru_json: str) -> None:
    with open(fru_json) as f:
        hpm_data = json.load(f)

    fru = HardwareComponent.model_validate(hpm_data)
    print(fru)


if __name__ == "__main__":
    app()
