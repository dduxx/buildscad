from pathlib import Path

import pytest

from buildscad.config import (
    load_properties,
    get_property,
    get_assemblies,
    load_deps,
    write_properties,
    write_deps,
    get_project_root,
    get_output_format,
    PROP_PROJECT,
    PROP_VERSION,
    PROP_AUTHOR,
    PROP_ASSEMBLIES,
    PROP_LOG_LEVEL,
    PROP_OPENSCAD_PATH,
    PROP_OUTPUT_FORMAT,
    DEFAULT_VALUES,
)
from buildscad.types import OutputType


def test_load_properties(initialized_project):
    props = load_properties(initialized_project)
    assert props[PROP_PROJECT] == initialized_project.name
    assert props[PROP_VERSION] == DEFAULT_VALUES[PROP_VERSION]
    assert props[PROP_AUTHOR] == DEFAULT_VALUES[PROP_AUTHOR]
    assert props[PROP_ASSEMBLIES] == DEFAULT_VALUES[PROP_ASSEMBLIES]


def test_load_properties_skips_comments(initialized_project):
    props = load_properties(initialized_project)
    assert PROP_LOG_LEVEL not in props
    assert PROP_OPENSCAD_PATH not in props


def test_get_property(initialized_project):
    assert get_property(PROP_PROJECT, project_root=initialized_project) == initialized_project.name
    assert get_property(PROP_VERSION, project_root=initialized_project) == DEFAULT_VALUES[PROP_VERSION]


def test_get_property_default(project_root):
    project_root.joinpath("buildscad.properties").write_text(f"{PROP_PROJECT}=custom\n")
    assert get_property(PROP_PROJECT, project_root=project_root) == "custom"
    assert get_property("NONEXISTENT", default="fallback", project_root=project_root) == "fallback"


def test_get_assemblies_single(initialized_project):
    assemblies = get_assemblies(project_root=initialized_project)
    assert assemblies == ["scad/main.scad"]


def test_get_assemblies_multiple(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_ASSEMBLIES}=scad/main.scad,scad/bracket.scad\n"
    )
    assemblies = get_assemblies(project_root=project_root)
    assert assemblies == ["scad/main.scad", "scad/bracket.scad"]


def test_load_deps(initialized_project):
    deps = load_deps(initialized_project)
    assert deps == []


def test_load_deps_with_entries(project_root):
    write_deps([{"url": "https://github.com/test/repo", "ref": "v1.0"}], project_root)
    deps = load_deps(project_root)
    assert len(deps) == 1
    assert deps[0]["url"] == "https://github.com/test/repo"
    assert deps[0]["ref"] == "v1.0"


def test_load_deps_invalid_format(project_root):
    project_root.joinpath("deps.json").write_text('{"not": "an array"}')
    with pytest.raises(ValueError, match="must contain a JSON array"):
        load_deps(project_root)


def test_write_properties(project_root):
    props = {
        PROP_PROJECT: "test-project",
        PROP_VERSION: "2.0.0",
        PROP_AUTHOR: "testuser",
        PROP_ASSEMBLIES: "scad/main.scad",
        PROP_LOG_LEVEL: "DEBUG",
        PROP_OPENSCAD_PATH: "/opt/openscad",
    }
    write_properties(props, project_root)
    content = project_root.joinpath("buildscad.properties").read_text()
    assert f"{PROP_PROJECT}=test-project" in content
    assert f"# {PROP_LOG_LEVEL}=DEBUG" in content
    assert f"# {PROP_OPENSCAD_PATH}=/opt/openscad" in content


def test_write_deps(project_root):
    deps = [{"url": "https://github.com/a/b", "ref": "main"}]
    write_deps(deps, project_root)
    loaded = load_deps(project_root)
    assert loaded == deps


def test_get_project_root(initialized_project):
    import os
    original_cwd = os.getcwd()
    os.chdir(initialized_project)
    try:
        found = get_project_root()
        assert found == initialized_project
    finally:
        os.chdir(original_cwd)


def test_get_project_root_not_found(project_root):
    with pytest.raises(FileNotFoundError, match="buildscad.properties not found"):
        get_project_root()


def test_load_properties_not_found(project_root):
    with pytest.raises(FileNotFoundError, match="buildscad.properties not found"):
        load_properties(project_root)


def test_load_deps_not_found(project_root):
    with pytest.raises(FileNotFoundError, match="deps.json not found"):
        load_deps(project_root)


def test_get_output_format_default(initialized_project):
    fmt = get_output_format(project_root=initialized_project)
    assert fmt == OutputType.STL


def test_get_output_format_from_property(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OUTPUT_FORMAT}=3mf\n"
    )
    fmt = get_output_format(project_root=project_root)
    assert fmt == OutputType.THREE_MF


def test_get_output_format_cli_takes_precedence(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OUTPUT_FORMAT}=3mf\n"
    )
    fmt = get_output_format(cli_type="amf", project_root=project_root)
    assert fmt == OutputType.AMF


def test_get_output_format_invalid_cli(project_root):
    with pytest.raises(ValueError, match="not a valid output type"):
        get_output_format(cli_type="invalid")


def test_get_output_format_invalid_property(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OUTPUT_FORMAT}=badformat\n"
    )
    with pytest.raises(ValueError, match="Invalid BUILDSCAD_OUTPUT_FORMAT value"):
        get_output_format(project_root=project_root)
