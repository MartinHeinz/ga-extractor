# Google Analytics Extractor

## Running

```bash
python -m extractor --help
```

Setup:

```bash
python -m extractor setup \
  --sa-key-path="analytics-api-24102021-4edf0b7270c0.json" \
  --table-id="123456789" \
  --metrics="ga:sessions" \
  --dimensions="ga:browser" \
  --start-date="2022-03-15" \
  --end-date="2022-03-19"
```

## Testing

```bash
pytest
```