import pytest
from click.testing import CliRunner
from app.web.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_cli_search_help(runner):
    result = runner.invoke(cli, ["search", "--help"])
    assert result.exit_code == 0
    assert "Search" in result.output


def test_cli_stats_help(runner):
    result = runner.invoke(cli, ["stats", "--help"])
    assert result.exit_code == 0
    assert "statistics" in result.output.lower()


def test_cli_serve_help(runner):
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0
    assert "dashboard" in result.output


def test_cli_list_help(runner):
    result = runner.invoke(cli, ["list", "--help"])
    assert result.exit_code == 0
    assert "prospects" in result.output.lower()


def test_cli_export_help(runner):
    result = runner.invoke(cli, ["export", "--help"])
    assert result.exit_code == 0
    assert "JSON" in result.output or "export" in result.output


def test_cli_invalid_command(runner):
    result = runner.invoke(cli, ["nonexistent"])
    assert result.exit_code != 0


def test_cli_scrape_prospects_help(runner):
    result = runner.invoke(cli, ["scrape-prospects", "--help"])
    assert result.exit_code == 0
    assert "prospects" in result.output.lower()


def test_cli_match_help(runner):
    result = runner.invoke(cli, ["match", "--help"])
    assert result.exit_code == 0
    assert "Score" in result.output or "score" in result.output


def test_cli_set_profile_help(runner):
    result = runner.invoke(cli, ["set-profile", "--help"])
    assert result.exit_code == 0
    assert "profile" in result.output.lower()
