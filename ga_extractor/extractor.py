import json
import uuid

import typer
import validators
from googleapiclient.discovery import build
from google.oauth2 import service_account
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from typing import Optional, NamedTuple

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


class Preset(str, Enum):
    NONE = "NONE"
    FULL = "FULL"
    BASIC = "BASIC"

    @staticmethod
    def metrics(p):
        metrics_mapping = {
            Preset.NONE: [],
            Preset.FULL: ["ga:pageviews", "ga:sessions"],
            Preset.BASIC: ["ga:pageviews"],
        }
        return metrics_mapping[p]

    @staticmethod
    def dims(p):
        dims_mapping = {
            Preset.NONE: [],
            Preset.FULL: ["ga:pagePath", "ga:browser", "ga:operatingSystem", "ga:deviceCategory", "ga:browserSize",
                          "ga:language", "ga:country", "ga:fullReferrer"],
            Preset.BASIC: ["ga:pagePath"],
        }
        return dims_mapping[p]


@extractor.command()
def setup(metrics: str = typer.Option(None, "--metrics"),
          dimensions: str = typer.Option(None, "--dimensions"),
          sa_key_path: str = typer.Option(..., "--sa-key-path"),
          table_id: int = typer.Option(..., "--table-id"),
          sampling_level: SamplingLevel = typer.Option(SamplingLevel.DEFAULT, "--sampling-level"),
          preset: Preset = typer.Option(Preset.NONE, "--preset",
                                        help="Use metrics and dimension preset (can't be specified with '--dimensions' or '--metrics')"),
          start_date: datetime = typer.Option(..., formats=["%Y-%m-%d"]),
          end_date: datetime = typer.Option(..., formats=["%Y-%m-%d"]),
          dry_run: bool = typer.Option(False, "--dry-run", help="Outputs config to terminal instead of config file")):
    """
    Generate configuration file from arguments
    """

    if (
            (preset is Preset.NONE and dimensions is None and metrics is None) or
            (dimensions is None and metrics is not None) or (dimensions is not None and metrics is None)
    ):
        typer.echo("Dimensions and Metrics or Preset must be specified.")
        typer.Exit(2)

    config = {
        "serviceAccountKeyPath": sa_key_path,
        "table": table_id,
        "metrics": "" if not metrics else metrics.split(","),
        "dimensions": "" if not dimensions else dimensions.split(","),
        "samplingLevel": sampling_level.value,
        "startDate": f"{start_date:%Y-%m-%d}",
        "endDate": f"{end_date:%Y-%m-%d}",
    }

    if preset is not Preset.NONE:
        config["metrics"] = Preset.metrics(preset)
        config["dimensions"] = Preset.dims(preset)

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
    Extracts data based on the config
    """
    # https://developers.google.com/analytics/devguides/reporting/core/v4/rest/v4/reports/batchGet

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

        dimensions = [{"name": d} for d in config['dimensions']]
        metrics = [{"expression": m} for m in config['metrics']]
        body = {"reportRequests": [
                    {
                        # "pageSize": 2,  # Use this to test paging
                        "viewId": f"{config['table']}",
                        "dateRanges": [
                            {
                                "startDate": f"{config['startDate']}",
                                "endDate": f"{config['endDate']}"
                            }],
                        "dimensions": [dimensions],
                        "metrics": [metrics],
                        "samplingLevel": config['samplingLevel']
                    }]}
        rows = []
        with build('analyticsreporting', 'v4', credentials=scoped_credentials) as service:
            response = service.reports().batchGet(body=body).execute()
            if not "rows" in response.values():
                raise Exception("There were no rows in the response.")
            rows.extend(response["reports"][0]["data"]["rows"])

            while "nextPageToken" in response["reports"][0]:  # Paging...
                body["reportRequests"][0]["pageToken"] = response["reports"][0]["nextPageToken"]
                response = service.reports().batchGet(body=body).execute()
                rows.extend(response["reports"][0]["data"]["rows"])

            output_path.write_text(json.dumps(rows))
        typer.echo(f"Report written to {output_path.absolute()}")


@extractor.command()
def migrate(output_format: OutputFormat = typer.Option(OutputFormat.JSON, "--format"),
            umami_website_id: int = typer.Argument(1, help="Website ID, used if migrating data for Umami Analytics"),
            umami_hostname: str = typer.Argument("localhost", help="Hostname website being migrated, used if migrating data for Umami Analytics")):
    """
    Export necessary data and transform it to format for target environment (Umami, ...)

    Old sessions won't be preserved because session can span multiple days, but extraction is done on daily level.

    Bounce rate and session duration won't be accurate.
    Views and visitors on day-level granularity will be accurate.
    Exact visit time is (hour and minute) is not preserved.
    """

    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.yaml"
    output_path: Path = Path(app_dir) / f"{uuid.uuid4()}_extract.{OutputFormat.file_suffix(output_format)}"
    if not config_path.is_file():
        typer.echo("Config file doesn't exist yet. Please run 'setup' command first.")
        typer.Exit(2)
    with config_path.open() as file:
        config = yaml.safe_load(file)
        credentials = service_account.Credentials.from_service_account_file(config["serviceAccountKeyPath"])
        scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/analytics.readonly'])

        date_ranges = __migrate_date_ranges(config['startDate'], config['endDate'])
        rows = __migrate_extract(scoped_credentials, config['table'], date_ranges)

        if output_format == OutputFormat.UMAMI:
            data = __migrate_transform_umami(rows, umami_website_id, umami_hostname)
            with output_path.open(mode="w") as f:
                for insert in data:
                    f.write(f"{insert}\n")
        elif output_format == OutputFormat.JSON:
            output_path.write_text(json.dumps(rows))
        elif output_format == OutputFormat.CSV:
            data = __migrate_transform_csv(rows)
            with output_path.open(mode="w") as f:
                for row in data:
                    f.write(f"{row}\n")

        typer.echo(f"Report written to {output_path.absolute()}")


def __migrate_date_ranges(start_date, end_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    date_ranges = [{"startDate": f"{start_date + timedelta(days=d):%Y-%m-%d}",
                    "endDate": f"{start_date + timedelta(days=d):%Y-%m-%d}"} for d in
                   range(((end_date.date() - start_date.date()).days + 1))]
    return date_ranges


def __migrate_extract(credentials, table_id, date_ranges):
    dimensions = ["ga:pagePath", "ga:browser", "ga:operatingSystem", "ga:deviceCategory", "ga:browserSize", "ga:language", "ga:country", "ga:fullReferrer"]
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
            num_rows = response["reports"][0]["data"]["totals"][0]["values"]
            if len(list(filter(lambda x: x != '0', num_rows))):
                rows[r["startDate"]] = response["reports"][0]["data"]["rows"]

    return rows


class Session(NamedTuple):
    session_id: int
    session_uuid: uuid.UUID
    website_id: int
    created_at: str
    hostname: str
    browser: str
    os: str
    device: str
    screen: str
    language: str

    def sql(self):
        session_insert = (
            f"INSERT INTO public.session (session_id, session_uuid, website_id, created_at, hostname, browser, os, device, screen, language, country) "
            f"VALUES ({self.session_id}, '{self.session_uuid}', {self.website_id}, '{self.created_at}', '{self.hostname}', '{self.browser[:20]}', '{self.os}', '{self.device}', '{self.screen}', '{self.language}', NULL);"
        )
        return session_insert


class PageView(NamedTuple):
    id: int
    website_id: int
    session_id: int
    created_at: str
    url: str
    referral_path: str

    def sql(self):
        return f"INSERT INTO public.pageview (view_id, website_id, session_id, created_at, url, referrer) VALUES ({self.id}, {self.website_id}, {self.session_id}, '{self.created_at}', '{self.url}', '{self.referral_path}');"


def __migrate_transform_umami(rows,  website_id, hostname):

    # Sample row:
    # {'dimensions': ['/', 'Chrome', 'Windows', 'desktop', '1350x610', 'en-us', 'India', '(direct)'], 'metrics': [{'values': ['1', '1']}]}
    #
    # Notes: there can be 0 sessions in the record; there's always more or equal number of views
    #        - treat zero sessions as one
    #        - if sessions is non-zero and page views are > 1, then divide, e.g.:
    #           - 5, 5 - 5 sessions, 1 view each
    #           - 4, 2 - 2 sessions, 2 views each
    #           - 5, 3 - 3 sessions, 2x1 view, 1x3 views

    page_view_id = 1
    session_id = 1
    sql_inserts = []
    for day, value in rows.items():
        for row in value:
            timestamp = f"{day} 00:00:00.000+00"  # PostgreSQL-style "timestamp with timezone"
            referrer = f"https://{row['dimensions'][7]}"
            if not validators.url(referrer):
                referrer = ""
            elif referrer == "google":
                referrer = "https://google.com"

            language = row["dimensions"][5][:2]
            page_views, sessions = map(int, row["metrics"][0]["values"])
            sessions = max(sessions, 1)  # in case it's zero
            if page_views == sessions:  # One page view for each session
                for i in range(sessions):
                    s = Session(session_uuid=uuid.uuid4(), session_id=session_id, website_id=website_id, created_at=timestamp, hostname=hostname,
                                browser=row["dimensions"][1], os=row["dimensions"][2], device=row["dimensions"][3], screen=row["dimensions"][4],
                                language=language)
                    p = PageView(id=page_view_id, website_id=website_id, session_id=session_id, created_at=timestamp, url=row["dimensions"][0], referral_path=referrer)
                    sql_inserts.extend([s.sql(), p.sql()])
                    session_id += 1
                    page_view_id += 1

            elif page_views % sessions == 0:  # Split equally
                for i in range(sessions):
                    s = Session(session_uuid=uuid.uuid4(), session_id=session_id, website_id=website_id, created_at=timestamp, hostname=hostname,
                                browser=row["dimensions"][1], os=row["dimensions"][2], device=row["dimensions"][3], screen=row["dimensions"][4],
                                language=language)
                    sql_inserts.append(s.sql())
                    for j in range(page_views // sessions):
                        p = PageView(id=page_view_id, website_id=website_id, session_id=session_id, created_at=timestamp, url=row["dimensions"][0], referral_path=referrer)
                        sql_inserts.append(p.sql())
                        page_view_id += 1
                    session_id += 1
            else:  # One page view for each, rest for the last session
                for i in range(sessions):
                    s = Session(session_uuid=uuid.uuid4(), session_id=session_id, website_id=website_id, created_at=timestamp, hostname=hostname,
                                browser=row["dimensions"][1], os=row["dimensions"][2], device=row["dimensions"][3], screen=row["dimensions"][4],
                                language=language)
                    p = PageView(id=page_view_id, website_id=website_id, session_id=session_id, created_at=timestamp, url=row["dimensions"][0], referral_path=referrer)
                    sql_inserts.extend([s.sql(), p.sql()])
                    session_id += 1
                    page_view_id += 1
                last_session_id = session_id - 1
                for i in range(page_views - sessions):
                    p = PageView(id=page_view_id, website_id=website_id, session_id=last_session_id, created_at=timestamp, url=row["dimensions"][0], referral_path=referrer)
                    page_view_id += 1
                    sql_inserts.append(p.sql())

    sql_inserts.extend([
        f"SELECT pg_catalog.setval('public.pageview_view_id_seq', {page_view_id}, true);",
        f"SELECT pg_catalog.setval('public.session_session_id_seq', {session_id}, true);"
    ])
    return sql_inserts


class CSVRow(NamedTuple):
    path: str
    browser: str
    os: str
    device: str
    screen: str
    language: str
    country: str
    referral_path: str
    count: str
    date: datetime.date

    @staticmethod
    def header():
        return f"path,browser,os,device,screen,language,country,referral_path,count,date"

    def csv(self):
        return f"{self.path},{self.browser},{self.os},{self.device},{self.screen},{self.language},{self.country},{self.referral_path},{self.count},{self.date}"


def __migrate_transform_csv(rows):
    csv_rows = [CSVRow.header()]
    for day, value in rows.items():
        for row in value:
            page_views, _ = map(int, row["metrics"][0]["values"])
            row = CSVRow(path=row["dimensions"][0],
                         browser=row["dimensions"][1],
                         os=row["dimensions"][2],
                         device=row["dimensions"][3],
                         screen=row["dimensions"][4],
                         language=row["dimensions"][5],
                         country=row["dimensions"][6],
                         referral_path=row["dimensions"][7],
                         count=page_views,
                         date=day)
            csv_rows.append(row.csv())
    return csv_rows
