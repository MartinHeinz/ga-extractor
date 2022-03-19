import typer

extractor = typer.Typer()


@extractor.command()
def hello(name: str):
    typer.echo(f"Hello {name}")


@extractor.command()
def goodbye(name: str, formal: bool = False):
    if formal:
        typer.echo(f"Goodbye Ms. {name}. Have a good day.")
    else:
        typer.echo(f"Bye {name}!")

