from typer.testing import CliRunner

from .context import extractor

runner = CliRunner()

# https://typer.tiangolo.com/tutorial/testing/
def test_app(capsys):
    result = runner.invoke(extractor.extractor, ["hello", "John"])
    assert result.exit_code == 0
    assert "Hello John" in result.stdout
