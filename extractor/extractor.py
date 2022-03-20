import typer
from googleapiclient.discovery import build
from google.oauth2 import service_account
import yaml
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Optional

extractor = typer.Typer()
APP_NAME = "ga-extractor"


class SamplingLevel(str, Enum):
    SAMPLING_UNSPECIFIED = "SAMPLING_UNSPECIFIED"
    DEFAULT = "DEFAULT"
    SMALL = "SMALL"
    LARGE = "LARGE"


@extractor.command()
def setup(metrics: str = typer.Option(..., "--metrics"),
          dimensions: str = typer.Option(..., "--dimensions"),
          sa_key_path: str = typer.Option(..., "--sa-key-path"),
          table_id: int = typer.Option(..., "--table-id"),
          filters: Optional[str] = typer.Option(None, "--filters"),
          sampling_level: SamplingLevel = typer.Option(SamplingLevel.DEFAULT, "--sampling-level"),
          start_date: datetime = typer.Option(..., formats=["%Y-%m-%d"]),
          end_date: datetime = typer.Option(..., formats=["%Y-%m-%d"]),
          path: str = typer.Option("config.yaml", "--path", help="Path for config file that will be generated"),
          dry_run: bool = typer.Option(False, "--dry-run", help="Outputs config to terminal instead of config file")):
    """
    Generate configuration file from arguments
    """

    config = {
        "serviceAccountKeyPath": sa_key_path,
        "table": table_id,
        "metrics": metrics,
        "dimensions": dimensions,
        "filters": "" if not filters else filters,
        "samplingLevel": sampling_level.value,
        "startDate": f"{start_date:%Y-%m-%d}",
        "endDate": f"{end_date:%Y-%m-%d}",
    }

    my_file = Path(sa_key_path)
    if not my_file.is_file():
        typer.echo(f"The service account key file ({sa_key_path}) doesn't exist.")
        return

    output = yaml.dump(config)
    if dry_run:
        typer.echo(output)
    else:
        with open(path, 'w') as outfile:
            outfile.write(output)


@extractor.command()
def auth():
    """
    Test authentication using generated configuration
    """
    try:
        credentials = service_account.Credentials.from_service_account_file("SOME_PATH.json")  # TODO Read this from config
        scoped_credentials = credentials.with_scopes(['openid'])
        with build('oauth2', 'v2', credentials=scoped_credentials) as service:
            user_info = service.userinfo().v2().me().get().execute()
            typer.echo(f"Successfully authenticated with user: {user_info['id']}")
    except BaseException as e:
        typer.echo(f"Authenticated failed with error: '{e}'")


@extractor.command()
def extract():
    ...
    # Extract data based on the config
    # Provide flags for overrides
    # Args: Output File
    # https://developers.google.com/analytics/devguides/reporting/core/v4

    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.yaml"
    if not config_path.is_file():
        typer.echo("Config file doesn't exist yet. Please run 'setup' command first.")


@extractor.command()
def _import():
    ...
    # Import data into selected backend (PostgreSQL, Umami, ...)
    # Args: output to File/Terminal
