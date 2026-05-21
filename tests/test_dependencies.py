import pytest

from buildscad.dependencies import (
    sanitize_name,
    parse_github_url,
    get_dependency_dir_name,
)


def test_sanitize_name_basic():
    assert sanitize_name("valid-name_1.0") == "valid-name_1.0"


def test_sanitize_name_replaces_slash():
    assert sanitize_name("feature/branch") == "feature_branch"


def test_sanitize_name_replaces_colon():
    assert sanitize_name("v1:0:0") == "v1_0_0"


def test_sanitize_name_replaces_spaces():
    assert sanitize_name("my branch name") == "my_branch_name"


def test_parse_github_url_https():
    author, project = parse_github_url("https://github.com/rcolyer/threads-scad")
    assert author == "rcolyer"
    assert project == "threads-scad"


def test_parse_github_url_https_trailing_git():
    author, project = parse_github_url("https://github.com/rcolyer/threads-scad.git")
    assert author == "rcolyer"
    assert project == "threads-scad"


def test_parse_github_url_https_trailing_slash():
    author, project = parse_github_url("https://github.com/rcolyer/threads-scad/")
    assert author == "rcolyer"
    assert project == "threads-scad"


def test_parse_github_url_ssh():
    author, project = parse_github_url("git@github.com:nophead/NopSCADlib")
    assert author == "nophead"
    assert project == "NopSCADlib"


def test_parse_github_url_ssh_trailing_git():
    author, project = parse_github_url("git@github.com:nophead/NopSCADlib.git")
    assert author == "nophead"
    assert project == "NopSCADlib"


def test_parse_github_url_invalid():
    with pytest.raises(ValueError, match="Unsupported GitHub URL"):
        parse_github_url("https://gitlab.com/some/repo")


def test_parse_github_url_too_short():
    with pytest.raises(ValueError, match="Invalid GitHub URL"):
        parse_github_url("https://github.com/onlyauthor")


def test_get_dependency_dir_name():
    name = get_dependency_dir_name("https://github.com/rcolyer/threads-scad", "v2.0.0")
    assert name == "rcolyer:threads-scad:v2.0.0"


def test_get_dependency_dir_name_sanitizes_ref():
    name = get_dependency_dir_name("https://github.com/rcolyer/threads-scad", "feature/new-thing")
    assert name == "rcolyer:threads-scad:feature_new-thing"
