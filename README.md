# Google Analytics Extractor

## Google Cloud API Access

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
  
## Running

```bash
python -m ga_extractor --help
```

Setup:

```bash
python -m ga_extractor setup \
  --sa-key-path="analytics-api-24102021-4edf0b7270c0.json" \
  --table-id="123456789" \
  --metrics="ga:sessions" \
  --dimensions="ga:browser" \
  --start-date="2022-03-15" \
  --end-date="2022-03-19"
  
cat ~/.config/ga-extractor/config.yaml  # Optionally, check config

python -m ga_extractor auth  # Test authentication
Successfully authenticated with user: ...
```

Value for `--table-id` can be found in GA web console - Click on _Admin_ section, _View Settings_ and see _View ID_ field 

Extract:

```bash
python -m ga_extractor extract
# Report written to /home/some-user/.config/ga-extractor/report.json
```

Migrate:

```bash
python -m ga_extractor migrate --format=UMAMI
# Report written to /home/user/.config/ga-extractor/cee9e1d0-3b87-4052-a295-1b7224c5ba78_extract.sql

cat cee9e1d0-3b87-4052-a295-1b7224c5ba78_extract.sql | docker exec -i db psql -Upostgres -a blog
```

This should be run against clean database, consider running following if possible

```sql
-- THIS WILL WIPE YOUR DATA
TRUNCATE public.pageview RESTART IDENTITY CASCADE;
TRUNCATE public.session RESTART IDENTITY CASCADE;
```

You can verify the data is correct in Umami web console and GA web console:

- [Umami extract](./assets/umami-migration.png)
- [GA Pageviews](./assets/ga-pageviews.png)

_Note: Some data in GA and Umami web console might be little off, because GA displays many metrics based on sessions (e.g. Sessions by device), but data is extracted/migrated based on page views. You can however confirm that percentage breakdown of browser or OS usage does match._

## Testing

```bash
pytest
```

## Building Package

```bash
poetry install
ga-extractor --help

# Usage: ga-extractor [OPTIONS] COMMAND [ARGS]...
# ...
```