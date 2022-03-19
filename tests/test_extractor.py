from .context import extractor


def test_app(capsys):
    # pylint: disable=W0612,W0613
    extractor.Extractor.run()
    captured = capsys.readouterr()

    assert "Hello World..." in captured.out