"""Tests for the configuration module and the package's lazy exports."""

import importlib

import pytest

import config

# --------------------------------------------------------------------------
# Dotenv reading
# --------------------------------------------------------------------------


def test_load_dotenv_returns_empty_for_missing_file(tmp_path):
    assert config._load_dotenv(tmp_path / "nope.env") == {}


def test_load_dotenv_parses_assignments(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "\n".join(
            [
                "# a comment",
                "",
                "PLAIN=value",
                'QUOTED="quoted value"',
                "SINGLE='single value'",
                "  SPACED  =  trimmed  ",
                "EQUALS=a=b",
                "no_equals_sign",
            ]
        ),
        encoding="utf-8",
    )
    values = config._load_dotenv(path)
    assert values["PLAIN"] == "value"
    assert values["QUOTED"] == "quoted value"
    assert values["SINGLE"] == "single value"
    assert values["SPACED"] == "trimmed"
    assert values["EQUALS"] == "a=b"
    assert "no_equals_sign" not in values


# --------------------------------------------------------------------------
# Setting getters
# --------------------------------------------------------------------------


def test_get_setting_returns_default_when_absent(monkeypatch):
    monkeypatch.delenv("QH_TEST_ABSENT", raising=False)
    assert config.get_setting("QH_TEST_ABSENT", "fallback") == "fallback"


def test_get_setting_prefers_the_environment(monkeypatch):
    monkeypatch.setenv("QH_TEST_PRESENT", "from-env")
    assert config.get_setting("QH_TEST_PRESENT", "fallback") == "from-env"


def test_get_int_parses_and_falls_back(monkeypatch):
    monkeypatch.setenv("QH_TEST_INT", "17")
    assert config.get_int("QH_TEST_INT", 5) == 17

    monkeypatch.setenv("QH_TEST_INT", "not-a-number")
    assert config.get_int("QH_TEST_INT", 5) == 5

    monkeypatch.delenv("QH_TEST_INT", raising=False)
    assert config.get_int("QH_TEST_INT", 5) == 5


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on"])
def test_get_bool_accepts_truthy_strings(monkeypatch, raw):
    monkeypatch.setenv("QH_TEST_BOOL", raw)
    assert config.get_bool("QH_TEST_BOOL", False) is True


@pytest.mark.parametrize("raw", ["0", "false", "no", "off", "maybe"])
def test_get_bool_rejects_other_strings(monkeypatch, raw):
    monkeypatch.setenv("QH_TEST_BOOL", raw)
    assert config.get_bool("QH_TEST_BOOL", True) is False


def test_get_bool_returns_default_when_absent(monkeypatch):
    monkeypatch.delenv("QH_TEST_BOOL", raising=False)
    assert config.get_bool("QH_TEST_BOOL", True) is True


# --------------------------------------------------------------------------
# Config dataclass
# --------------------------------------------------------------------------


def test_config_defaults_are_sane():
    settings = config.Config()
    assert settings.port == 5000
    assert settings.page_size == 10
    assert settings.max_page_size == 100
    assert settings.page_size <= settings.max_page_size
    assert settings.templates_folder == "templates"
    assert settings.static_folder == "static"


def test_config_reads_the_environment(monkeypatch):
    monkeypatch.setenv("PORT", "8123")
    monkeypatch.setenv("DEBUG", "true")
    assert config.Config().port == 8123
    assert config.Config().debug is True


def test_config_paths_point_at_the_data_directory():
    settings = config.Config()
    assert settings.papers_path.name == "papers.json"
    assert settings.projects_path.name == "projects.json"
    assert settings.papers_path.exists()
    assert settings.projects_path.exists()


def test_as_flask_config_exposes_the_expected_keys():
    exported = config.Config().as_flask_config()
    assert set(exported) == {
        "SECRET_KEY",
        "DEBUG",
        "TESTING",
        "JSON_SORT_KEYS",
        "PAGE_SIZE",
        "MAX_PAGE_SIZE",
        "MAX_SEARCH_RESULTS",
    }
    assert isinstance(exported["SECRET_KEY"], str)


# --------------------------------------------------------------------------
# Package exports
# --------------------------------------------------------------------------


def test_package_exposes_paper_symbols():
    package = importlib.import_module("quantumhub")
    assert package.Paper.__name__ == "Paper"
    assert package.PaperRepository.__name__ == "PaperRepository"


def test_package_exposes_project_symbols():
    package = importlib.import_module("quantumhub")
    assert package.Project.__name__ == "Project"
    assert package.ProjectRepository.__name__ == "ProjectRepository"


def test_package_exposes_a_version():
    package = importlib.import_module("quantumhub")
    assert package.__version__
    assert package.__author__


def test_package_rejects_unknown_attributes():
    package = importlib.import_module("quantumhub")
    with pytest.raises(AttributeError):
        package.NotAThing
