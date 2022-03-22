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

Value for `--table-id` can be found in GA web console - click on _Admin_ section, _View Settings_ and see _View ID_ field 

Extract:

```bash
python -m ga_extractor extract
# Report written to /home/some-user/.config/ga-extractor/report.json
```

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