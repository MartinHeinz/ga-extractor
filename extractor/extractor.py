import typer
from googleapiclient.discovery import build
from google.oauth2 import service_account

extractor = typer.Typer()


@extractor.command()
def setup():
    ...
    # Generate configuration file from arguments
    # https://martinheinz.dev/blog/62
    # args: dimensions, date range, metric (page views or sessions), filter, profile (View/Table ID), credentials path (service account key)


@extractor.command()
def auth():
    # Test authentication using generated configuration
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
