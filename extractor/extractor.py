import typer

extractor = typer.Typer()


@extractor.command()
def setup():
    ...
    # Generate configuration file from arguments
    # https://martinheinz.dev/blog/62
    # args: dimensions, date range, metric (page views or sessions), filter, profile (View/Table ID), credentials path (service account key)


@extractor.command()
def test():
    ...
    # Test authentication using generated configuration


@extractor.command()
def extract():
    ...
    # Extract data based on the config
    # Provide flags for overrides
