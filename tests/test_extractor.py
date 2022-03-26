from typer.testing import CliRunner

from ga_extractor.extractor import __migrate_transform_umami, __migrate_transform_csv

runner = CliRunner()


def test__migrate_transform_umami(sample_extract):
    sql = __migrate_transform_umami(sample_extract, 1, "localhost")
    assert len(sql) == 25
    assert sum(1 if row.startswith("INSERT INTO public.session") else 0 for row in sql) == 10  # Sessions
    assert sum(1 if row.startswith("INSERT INTO public.pageview") else 0 for row in sql) == 13  # Sessions
    assert sum(1 if "/blog/68" in row else 0 for row in sql) == 3


def test__migrate_transform_csv(sample_extract):
    expected = ['path,browser,os,device,screen,language,country,referral_path,count,date',
                '/blog/69,Chrome,Linux,desktop,1850x950,es-us,Venezuela,t.co/,5,2022-03-19',
                '/,Chrome,Android,mobile,420x800,en-us,Malaysia,google,1,2022-03-19',
                '/blog/51,Chrome,Macintosh,desktop,1540x850,en-us,United States,(direct),4,2022-03-19',
                '/blog/68,Firefox,Android,mobile,410x780,es-us,Colombia,betterprogramming.pub/building-github-apps-with-golang-43b27f3e9621,3,2022-03-19']

    csv_rows = __migrate_transform_csv(sample_extract)

    assert csv_rows == expected
