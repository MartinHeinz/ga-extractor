import json

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

    output = yaml.dump(config)
    if dry_run:
        typer.echo(output)
    else:
        app_dir = typer.get_app_dir(APP_NAME)
        config_path: Path = Path(app_dir) / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as outfile:
            outfile.write(output)


@extractor.command()
def auth():
    """
    Test authentication using generated configuration
    """
    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.yaml"
    if not config_path.is_file():
        typer.echo("Config file doesn't exist yet. Please run 'setup' command first.")
        return
    try:
        with config_path.open() as config:
            credentials = service_account.Credentials.from_service_account_file(yaml.safe_load(config)["serviceAccountKeyPath"])
            scoped_credentials = credentials.with_scopes(['openid'])
        with build('oauth2', 'v2', credentials=scoped_credentials) as service:
            user_info = service.userinfo().v2().me().get().execute()
            typer.echo(f"Successfully authenticated with user: {user_info['id']}")
    except BaseException as e:
        typer.echo(f"Authenticated failed with error: '{e}'")


@extractor.command()
def extract(report: Optional[Path] = typer.Option("report.json", dir_okay=True)):
    """
    # Extracts data based on the config
    """
    # https://developers.google.com/analytics/devguides/reporting/core/v4

    # TODO Provide flags for overrides
    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.yaml"
    output_path: Path = Path(app_dir) / report
    if not config_path.is_file():
        typer.echo("Config file doesn't exist yet. Please run 'setup' command first.")
    with config_path.open() as file:
        config = yaml.safe_load(file)
        credentials = service_account.Credentials.from_service_account_file(config["serviceAccountKeyPath"])
        scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/analytics.readonly'])

        dimensions = [{"name": d} for d in config['dimensions'].split(",")]
        metrics = [{"expression": m} for m in config['metrics'].split(",")]
        body = {"reportRequests": [
                    {
                        # "pageSize": 2,
                        "viewId": f"{config['table']}",
                        "dateRanges": [
                            {
                                "startDate": f"{config['startDate']}",
                                "endDate": f"{config['endDate']}"
                            }],
                        "dimensions": [dimensions],
                        "metrics": [metrics]
                    }]}

        rows = []
        with build('analyticsreporting', 'v4', credentials=scoped_credentials) as service:
            response = service.reports().batchGet(body=body).execute()
            rows.extend(response["reports"][0]["data"]["rows"])

            while "nextPageToken" in response["reports"][0]:
                body["reportRequests"][0]["pageToken"] = response["reports"][0]["nextPageToken"]
                response = service.reports().batchGet(body=body).execute()
                rows.extend(response["reports"][0]["data"]["rows"])

            output_path.write_text(json.dumps(rows))
        typer.echo(f"Report written to {output_path.absolute()}")


@extractor.command()
def _import():
    ...
    # Import data into selected backend (PostgreSQL, Umami, ...)
    # Args: output to File/Terminal
