import json
import uuid
from collections import namedtuple

import typer
from googleapiclient.discovery import build
from google.oauth2 import service_account
import yaml
from datetime import datetime, timedelta
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


class OutputFormat(str, Enum):
    JSON = "JSON"
    CSV = "CSV"
    UMAMI = "UMAMI"

    @staticmethod
    def file_suffix(f):
        format_mapping = {
            OutputFormat.JSON: "json",
            OutputFormat.CSV: "csv",
            OutputFormat.UMAMI: "sql",
        }
        return format_mapping[f]


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


# TODO include common reports:
#      Dims:    ga:referralPath, ga:source, ga:medium, ga:browser, ga:operatingSystem, ga:country, ga:language
#      Metrics: ga:users, ga:sessions, ga:hits, ga:pageviews
#      Presets: Full (all metrics, all dims for configured range), DailyWalk (same as migrate), Minimal (page views per day)
@extractor.command()
def extract(report: Optional[Path] = typer.Option("report.json", dir_okay=True)):
    """
    Extracts data based on the config
    """
    # https://developers.google.com/analytics/devguides/reporting/core/v4

    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.yaml"
    output_path: Path = Path(app_dir) / report
    if not config_path.is_file():
        typer.echo("Config file doesn't exist yet. Please run 'setup' command first.")
        typer.Exit(2)
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


# TODO: Instead of transformation of adhoc exports, transform only exports that fit into particular output type
@extractor.command()
def transform(infile: Optional[Path] = typer.Option("report.json", dir_okay=True),
              outfile: Optional[Path] = typer.Option(""),
              outformat: OutputFormat = typer.Option(OutputFormat.JSON, "--output-format"),):
    """
    Transforms extracted data to other formats (e.g. CSV, SQL)
    """
    app_dir = typer.get_app_dir(APP_NAME)
    input_path: Path = Path(app_dir) / infile  # TODO Allow for absolute path (files outside of config folder)
    if not input_path.is_file():
        typer.echo("Input file doesn't exist. Please run 'extract' command first.")
        typer.Exit(2)
    stdout = True
    if outfile:
        stdout = False
        output_path: Path = Path(app_dir) / outfile  # TODO Allow for absolute path (files outside of config folder)

    with input_path.open() as infile:
        # TODO Add missing column names (change in extract first)
        result = ""
        if outformat is OutputFormat.csv:
            # TODO Transform data to CSV matrix
            report = json.load(infile)
            for row in report:
                dims = row["dimensions"]
                metrics = row["metrics"][0]["values"]
                typer.echo(f"dims: {dims}, metrics: {metrics}")
        else:
            typer.echo(f"Invalid output format: {outformat}")
            typer.Exit(2)

        if stdout:
            typer.echo(result)
        else:
            with output_path.open(mode="w") as outfile:
                outfile.write(result)
                typer.echo(f"Report written to {output_path.absolute()}")


# TODO
@extractor.command()
def migrate(outputFormat: OutputFormat = typer.Option(OutputFormat.JSON, "--format")):
    """
    Export necessary data and transform it to format for target environment (Umami, ...)
    """
    # Query data per day (startDate/endDate same, multiple data ranges can be included in single query)
    # Generate the views + sessions based on the data, ignoring exact visit time
    # Old sessions won't be preserved, bounce rate and session duration won't be accurate; Views and visitors on day-level granularity with be accurate
    # TODO Transform, Insert, Test

    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.yaml"
    output_path: Path = Path(app_dir) / f"{uuid.uuid4()}_extract.{OutputFormat.file_suffix(outputFormat)}"
    if not config_path.is_file():
        typer.echo("Config file doesn't exist yet. Please run 'setup' command first.")
        typer.Exit(2)
    with config_path.open() as file:
        config = yaml.safe_load(file)
        credentials = service_account.Credentials.from_service_account_file(config["serviceAccountKeyPath"])
        scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/analytics.readonly'])

        date_ranges = _migrate_date_ranges(config['startDate'], config['endDate'])
        rows = __migrate_extract(scoped_credentials, config['table'], date_ranges)
        data = __migrate_transform(rows)

        output_path.write_text(json.dumps(data))
        typer.echo(f"Report written to {output_path.absolute()}")


def _migrate_date_ranges(start_date, end_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    date_ranges = [{"startDate": f"{start_date + timedelta(days=d):%Y-%m-%d}",
                    "endDate": f"{start_date + timedelta(days=d):%Y-%m-%d}"} for d in
                   range(((end_date.date() - start_date.date()).days + 1))]
    return date_ranges


def __migrate_extract(credentials, table_id, date_ranges):
    dimensions = ["ga:pagePath", "ga:browser", "ga:operatingSystem", "ga:deviceCategory", "ga:browserSize",
                  "ga:language", "ga:country"]
    metrics = ["ga:pageviews", "ga:sessions"]

    body = {"reportRequests": [
        {
            "viewId": f"{table_id}",
            "dimensions": [{"name": d} for d in dimensions],
            "metrics": [{"expression": m} for m in metrics]
        }]}

    rows = {}
    for r in date_ranges:
        with build('analyticsreporting', 'v4', credentials=credentials) as service:
            body["reportRequests"][0]["dateRanges"] = [r]
            response = service.reports().batchGet(body=body).execute()

            rows[date_ranges["startDate"]] = response["reports"][0]["data"]["rows"]

    return rows


def __migrate_transform(rows):
    # TODO transform rows to given format (SQL, CSV, Raw JSON)
    # For Umami:
    # INSERT INTO public.website (website_id, website_uuid, user_id, name, domain, share_id, created_at) VALUES (1, '...', 1, 'Blog', 'localhost', '...', '2022-02-22 15:07:31.4+00');
    # INSERT INTO public.session (session_id, session_uuid, website_id, created_at, hostname, browser, os, device, screen, language, country) VALUES (1, 'fff811c4-8991-5ae3-b4ba-34b75401db54', 1, '2022-02-22 15:14:14.323+00', 'localhost', 'chrome', 'Linux', 'desktop', '1920x1080', 'en', NULL);
    # INSERT INTO public.session (session_id, session_uuid, website_id, created_at, hostname, browser, os, device, screen, language, country) VALUES (2, 'fd2c990e-11b3-5bbe-9239-dae9556d1161', 1, '2022-02-23 12:03:36.126+00', 'localhost', 'chrome', 'Linux', 'desktop', '1920x1080', 'en', NULL);
    # INSERT INTO public.pageview (view_id, website_id, session_id, created_at, url, referrer) VALUES (1, 1, 1, '2022-02-22 15:14:14.327+00', '/', '/');
    # INSERT INTO public.pageview (view_id, website_id, session_id, created_at, url, referrer) VALUES (2, 1, 1, '2022-02-22 15:14:14.328+00', '/', '');
    # INSERT INTO public.pageview (view_id, website_id, session_id, created_at, url, referrer) VALUES (3, 1, 2, '2022-02-23 12:03:36.135+00', '/blog/53', '');
    # INSERT INTO public.pageview (view_id, website_id, session_id, created_at, url, referrer) VALUES (4, 1, 2, '2022-02-23 12:04:07.279+00', '/blog/54', '/blog/54');
    # SELECT pg_catalog.setval('public.pageview_view_id_seq', 4, true);
    # SELECT pg_catalog.setval('public.session_session_id_seq', 2, true);
    # SELECT pg_catalog.setval('public.website_website_id_seq', 1, true);

    # {'dimensions': ['/blog/29', 'Opera', 'Windows', 'desktop', '2520x1320', 'de-de', 'Germany'], 'metrics': [{'values': ['4', '1']}]}
    # Notes: there can be 0 sessions in the record; there's always more or equal number of views
    #        - treat zero sessions as one
    #        - if sessions is non-zero and page views are > 1, then divide, e.g.:
    #           - 5, 5 - 5 sessions, 1 view each
    #           - 4, 2 - 2 sessions, 1 view each
    #           - 5, 3 - 3 sessions, 2x1 view, 1x3 views
    website_id = 1
    hostname = "localhost"
    PageView = namedtuple('PageView', ["id", "website_id", "session_id", "created_at", "url"])
    Session = namedtuple('Session', ["session_id", "session_uuid", "website_id", "created_at", "hostname", "browser", "os", "device", "screen", "language", "country"])
    page_view_id = 1
    records = []
    # TODO Loop through sessions/page views (or multiply records)
    for i, (k, v) in enumerate(rows.items()):
        s = Session(session_uuid=uuid.uuid4(),
                    session_id=i,
                    website_id=website_id,
                    created_at=k,
                    hostname=hostname,
                    browser=v["dimensions"][1],
                    os=v["dimensions"][2],
                    device=v["dimensions"][3],
                    screen=v["dimensions"][4],
                    language=v["dimensions"][5],
                    country=v["dimensions"][6])
        p = PageView(id=page_view_id, website_id=website_id, session_id=i, created_at=k, url=v["dimensions"][0])
        page_view_id += 1
        session_insert = (
            f"INSERT INTO public.session (session_id, session_uuid, website_id, created_at, hostname, browser, os, device, screen, language, country) "
            f"VALUES ({s.session_id}, {s.session_uuid}, {s.website_id}, {s.created_at}, {s.hostname}, {s.browser}, {s.os}, {s.device}, {s.screen}, {s.language}, {s.country});"
        )
        page_insert = f"INSERT INTO public.pageview (view_id, website_id, session_id, created_at, url, referrer) VALUES ({p.id}, {p.website_id}, {p.session_id}, {p.created_at}, {p.url}, NULL);"
        records.append(session_insert)
        records.append(page_insert)
        typer.echo(session_insert)
        typer.echo(page_insert)
