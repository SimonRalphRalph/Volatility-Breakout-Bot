import typer
from rich import print

app = typer.Typer(add_completion=False)

@app.command()
def main(mode: str = "paper", run_id: str = "20250907"):
    print(f"[green]Run {run_id} mode={mode} (stub)[/green]")

if __name__ == "__main__":
    app()
