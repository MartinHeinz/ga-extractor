# Google Analytics Extractor

[![PyPI version](https://badge.fury.io/py/ga-extractor.svg)](https://badge.fury.io/py/ga-extractor)

A CLI tool for extracting Google Analytics data using Google Reporting API. Can be also used to transform data to various formats suitable for migration to other analytics platforms.

## Setup

You will need Google Cloud API access for run the CLI:

- Navigate to [Cloud Resource Manager](https://console.cloud.google.com/cloud-resource-manager) and click _Create Project_
    - alternatively create project with `gcloud projects create $PROJECT_ID`
- Navigate to [Reporting API](https://console.cloud.google.com/apis/library/analyticsreporting.googleapis.com) and click _Enable_
- Create credentials:
    - Go to [credentials page](https://console.cloud.google.com/apis/credentials)
    - Click _Create credentials_, select _Service account_
    - Give it a name and make note of service account email. Click _Create and Continue_

    - Open [Service account page](https://console.cloud.google.com/iam-admin/serviceaccounts)
    - Select previously created service account, Open _Keys_ tab
    - Click _Add Key_ and _Create New Key_. Choose JSON format and download it. (store this **securely**)

- Give SA permissions to GA - [guide](https://support.google.com/analytics/answer/1009702#Add)
    - email: SA email from earlier
    - role: _Viewer_
  
Alternatively see <https://martinheinz.dev/blog/62>.

To install and run:

```bash
pip install ga-extractor
ga-extractor --help
```
  
## Running

```bash
ga-extractor --help
# Usage: ga-extractor [OPTIONS] COMMAND [ARGS]...
# ...

# Create config file:
ga-extractor setup \
  --sa-key-path="analytics-api-24102021-4edf0b7270c0.json" \
  --table-id="123456789" \
  --metrics="ga:sessions" \
  --dimensions="ga:browser" \
  --start-date="2022-03-15" \
  --end-date="2022-03-19"
  
cat ~/.config/ga-extractor/config.yaml  # Optionally, check config

ga-extractor auth  # Test authentication
# Successfully authenticated with user: ...

ga-extractor setup --help  # For options and flags
```

- Value for `--table-id` can be found in GA web console - Click on _Admin_ section, _View Settings_ and see _View ID_ field
- All configurations and generated extracts/reports are stored in `~/.config/ga-extrator/...`
- You can also use metrics and dimensions presets using `--preset` with `FULL` or `BASIC`, if you're not sure which data to extract

### Extract

```bash
ga-extractor extract
# Report written to /home/some-user/.config/ga-extractor/report.json
```

`extract` perform raw extraction of dimensions and metrics using the provided configs

### Migrate

You can directly extract and transform data to various formats. Available options are:

- JSON (Default option; Default API output)
- CSV
- SQL (compatible with _Umami_ Analytics PostgreSQL backend)

```bash
ga-extractor migrate --format=CSV
# Report written to /home/user/.config/ga-extractor/02c2db1a-1ff0-47af-bad3-9c8bc51c1d13_extract.csv

head /home/user/.config/ga-extractor/02c2db1a-1ff0-47af-bad3-9c8bc51c1d13_extract.csv
# path,browser,os,device,screen,language,country,referral_path,count,date
# /,Chrome,Android,mobile,1370x1370,zh-cn,China,(direct),1,2022-03-18
# /,Chrome,Android,mobile,340x620,en-gb,United Kingdom,t.co/,1,2022-03-18

ga-extractor migrate --format=UMAMI
# Report written to /home/user/.config/ga-extractor/cee9e1d0-3b87-4052-a295-1b7224c5ba78_extract.sql

# IMPORTANT: Verify the data and check test database before inserting into production instance 
# To insert into DB (This should be run against clean database):
cat cee9e1d0-3b87-4052-a295-1b7224c5ba78_extract.sql | psql -Upostgres -a some-db
```

You can verify the data is correct in Umami web console and GA web console:

- [Umami extract](./assets/umami-migration.png)
- [GA Pageviews](./assets/ga-pageviews.png)

_Note: Some data in GA and Umami web console might be little off, because GA displays many metrics based on sessions (e.g. Sessions by device), but data is extracted/migrated based on page views. You can however confirm that percentage breakdown of browser or OS usage does match._

## Development

### Setup

Requirements:

- Poetry (+ virtual environment)

```bash
poetry install
python -m ga_extractor --help
```

### Testing

```bash
pytest
```

### Building Package

```bash
poetry install
ga-extractor --help

# Usage: ga-extractor [OPTIONS] COMMAND [ARGS]...
# ...
```