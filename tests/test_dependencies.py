import json
import pytest
from pathlib import Path
from unittest.mock import patch

from buildscad.dependencies import (
    sanitize_name,
    parse_github_url,
    get_dependency_dir_name,
    is_buildscad_project,
    install_all_dependencies,
    get_dependency_paths,
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


def test_is_buildscad_project_true(tmp_path):
    dep_path = tmp_path / "author:project:v1"
    dep_path.mkdir()
    dep_path.joinpath("buildscad.properties").write_text("BUILDSCAD_PROJECT=test\n")
    dep_path.joinpath("deps.json").write_text("[]")
    assert is_buildscad_project(dep_path) is True


def test_is_buildscad_project_false_no_properties(tmp_path):
    dep_path = tmp_path / "author:project:v1"
    dep_path.mkdir()
    dep_path.joinpath("deps.json").write_text("[]")
    assert is_buildscad_project(dep_path) is False


def test_is_buildscad_project_false_no_deps(tmp_path):
    dep_path = tmp_path / "author:project:v1"
    dep_path.mkdir()
    dep_path.joinpath("buildscad.properties").write_text("BUILDSCAD_PROJECT=test\n")
    assert is_buildscad_project(dep_path) is False


def test_is_buildscad_project_false_empty_dir(tmp_path):
    dep_path = tmp_path / "author:project:v1"
    dep_path.mkdir()
    assert is_buildscad_project(dep_path) is False


def _mock_install_dependency(url, ref, project_root, ignore_cache=False):
    deps_dir = project_root / "dependencies"
    deps_dir.mkdir(parents=True, exist_ok=True)
    dep_name = get_dependency_dir_name(url, ref)
    dep_path = deps_dir / dep_name
    dep_path.mkdir(parents=True, exist_ok=True)
    return dep_path


def test_install_all_dependencies_recursive(tmp_path):
    deps = [
        {"url": "https://github.com/authorA/depA", "ref": "v1"},
    ]

    sub_deps = [
        {"url": "https://github.com/authorC/depC", "ref": "v3"},
    ]

    def side_effect(url, ref, project_root, ignore_cache=False):
        dep_path = _mock_install_dependency(url, ref, project_root, ignore_cache)
        if ref == "v1":
            dep_path.joinpath("buildscad.properties").write_text("BUILDSCAD_PROJECT=depA\n")
            dep_path.joinpath("deps.json").write_text(json.dumps(sub_deps))
        return dep_path

    with patch("buildscad.dependencies.install_dependency", side_effect=side_effect):
        install_all_dependencies(deps, tmp_path)

    top_deps_dir = tmp_path / "dependencies"
    assert top_deps_dir.joinpath("authorA:depA:v1").exists()
    assert top_deps_dir.joinpath("authorC:depC:v3").exists()

    sub_dep_dir = top_deps_dir.joinpath("authorA:depA:v1", "dependencies")
    assert sub_dep_dir.exists()
    link = sub_dep_dir.joinpath("authorC:depC:v3")
    assert link.is_symlink()
    assert link.readlink() == Path("..").joinpath("authorC:depC:v3")


def test_install_all_dependencies_circular(tmp_path):
    deps_a = [
        {"url": "https://github.com/authorB/depB", "ref": "v1"},
    ]

    deps_b = [
        {"url": "https://github.com/authorA/depA", "ref": "v1"},
    ]

    call_count = {"count": 0}

    def side_effect(url, ref, project_root, ignore_cache=False):
        call_count["count"] += 1
        dep_path = _mock_install_dependency(url, ref, project_root, ignore_cache)
        if ref == "v1":
            dep_path.joinpath("buildscad.properties").write_text(f"BUILDSCAD_PROJECT={ref}\n")
            dep_path.joinpath("deps.json").write_text(json.dumps(deps_b))
        elif ref == "v2":
            dep_path.joinpath("buildscad.properties").write_text(f"BUILDSCAD_PROJECT={ref}\n")
            dep_path.joinpath("deps.json").write_text(json.dumps(deps_a))
        return dep_path

    with patch("buildscad.dependencies.install_dependency", side_effect=side_effect):
        install_all_dependencies(deps_a, tmp_path)

    assert call_count["count"] == 2


def test_install_all_dependencies_duplicate_transitive(tmp_path):
    deps = [
        {"url": "https://github.com/authorA/depA", "ref": "v1"},
        {"url": "https://github.com/authorB/depB", "ref": "v1"},
    ]

    shared_dep = {"url": "https://github.com/authorC/shared", "ref": "v2"}

    call_count = {"count": 0}

    def side_effect(url, ref, project_root, ignore_cache=False):
        call_count["count"] += 1
        dep_path = _mock_install_dependency(url, ref, project_root, ignore_cache)
        if ref in ("v1",):
            dep_path.joinpath("buildscad.properties").write_text(f"BUILDSCAD_PROJECT={ref}\n")
            dep_path.joinpath("deps.json").write_text(json.dumps([shared_dep]))
        return dep_path

    with patch("buildscad.dependencies.install_dependency", side_effect=side_effect):
        install_all_dependencies(deps, tmp_path)

    top_deps_dir = tmp_path / "dependencies"
    assert top_deps_dir.joinpath("authorC:shared:v2").exists()

    for dep_name in ("authorA:depA:v1", "authorB:depB:v1"):
        sub_dep_dir = top_deps_dir.joinpath(dep_name, "dependencies")
        assert sub_dep_dir.exists()
        link = sub_dep_dir.joinpath("authorC:shared:v2")
        assert link.is_symlink()


def test_install_all_dependencies_non_buildscad_dep(tmp_path):
    deps = [
        {"url": "https://github.com/authorA/plain-lib", "ref": "v1"},
    ]

    def side_effect(url, ref, project_root, ignore_cache=False):
        dep_path = _mock_install_dependency(url, ref, project_root, ignore_cache)
        return dep_path

    with patch("buildscad.dependencies.install_dependency", side_effect=side_effect):
        install_all_dependencies(deps, tmp_path)

    top_deps_dir = tmp_path / "dependencies"
    assert top_deps_dir.joinpath("authorA:plain-lib:v1").exists()
    assert not top_deps_dir.joinpath("authorA:plain-lib:v1", "dependencies").exists()


def test_get_dependency_paths_includes_symlinks(tmp_path):
    deps_dir = tmp_path / "dependencies"
    deps_dir.mkdir()

    real_dep = deps_dir / "authorA:depA:v1"
    real_dep.mkdir()

    link = deps_dir / "authorB:depB:v1"
    link.symlink_to(real_dep)

    paths = get_dependency_paths(tmp_path)
    assert len(paths) == 2
