from typer.testing import CliRunner

from .context import ga_extractor

runner = CliRunner()


# https://typer.tiangolo.com/tutorial/testing/
def test_app(capsys):
    result = runner.invoke(ga_extractor.extractor, ["hello", "John"])
    assert result.exit_code == 0
    assert "Hello John" in result.stdout
