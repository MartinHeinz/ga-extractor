from typer.testing import CliRunner

from ga_extractor.extractor import __migrate_transform

runner = CliRunner()


def test__migrate_transform():
    rows = {'2022-03-19': [
        {'dimensions': ['/blog/69', 'Chrome', 'Linux', 'desktop', '1850x950', 'es-us', 'Venezuela', 't.co/'], 'metrics': [{'values': ['5', '5']}]},
        {'dimensions': ['/', 'Chrome', 'Android', 'mobile', '420x800', 'en-us', 'Malaysia', 'google'], 'metrics': [{'values': ['1', '0']}]},
        {'dimensions': ['/blog/51', 'Chrome', 'Macintosh', 'desktop', '1540x850', 'en-us', 'United States', '(direct)'], 'metrics': [{'values': ['4', '2']}]},
        {'dimensions': ['/blog/68', 'Firefox', 'Android', 'mobile', '410x780', 'es-us', 'Colombia', 'betterprogramming.pub/building-github-apps-with-golang-43b27f3e9621'], 'metrics': [{'values': ['3', '2']}]},
    ]}

    sql = __migrate_transform(rows)
    print(sql)
    assert len(sql) == 25
    assert sum(1 if row.startswith("INSERT INTO public.session") else 0 for row in sql) == 10  # Sessions
    assert sum(1 if row.startswith("INSERT INTO public.pageview") else 0 for row in sql) == 13  # Sessions
    assert sum(1 if "/blog/68" in row else 0 for row in sql) == 3  # Sessions
    assert False