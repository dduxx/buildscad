import pytest

from buildscad.config import (
    load_properties,
    get_property,
    get_assemblies,
    load_deps,
    write_properties,
    write_deps,
    get_project_root,
    get_output_formats,
    get_openscad_path,
    get_colorscheme,
    get_openscad_version,
    _parse_assembly,
    _unescape_value,
    _sanitize_filename,
    Assembly,
    PROP_PROJECT,
    PROP_VERSION,
    PROP_AUTHOR,
    PROP_ASSEMBLIES,
    PROP_LOG_LEVEL,
    PROP_OPENSCAD_PATH,
    PROP_OUTPUT_FORMAT,
    PROP_OPENSCAD_COLORSCHEME,
    PROP_OPENSCAD_VERSION,
    DEFAULT_VALUES,
    ENV_OVERRIDABLE_PROPS,
)
from buildscad.types import OutputType
from buildscad.error import (
    BuildscadAssemblyParseError,
    BuildscadMissingConfigFile,
    BuildscadInvalidProperty,
    BuildscadInvalidOutputType,
)


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
    assert (
        get_property(PROP_VERSION, project_root=initialized_project) == DEFAULT_VALUES[PROP_VERSION]
    )


def test_get_property_default(project_root):
    project_root.joinpath("buildscad.properties").write_text(f"{PROP_PROJECT}=custom\n")
    assert get_property(PROP_PROJECT, project_root=project_root) == "custom"
    assert get_property("NONEXISTENT", default="fallback", project_root=project_root) == "fallback"


def test_get_assemblies_single(initialized_project):
    assemblies = get_assemblies(project_root=initialized_project)
    assert len(assemblies) == 1
    assert assemblies[0] == Assembly(path="scad/main.scad", variables={})


def test_get_assemblies_multiple(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_ASSEMBLIES}=scad/main.scad,scad/bracket.scad\n"
    )
    assemblies = get_assemblies(project_root=project_root)
    assert assemblies == [
        Assembly(path="scad/main.scad", variables={}),
        Assembly(path="scad/bracket.scad", variables={}),
    ]


def test_get_assemblies_with_variables(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_ASSEMBLIES}=scad/main.scad[threads=metric;diameter=8],scad/bracket.scad\n"
    )
    assemblies = get_assemblies(project_root=project_root)
    assert assemblies == [
        Assembly(path="scad/main.scad", variables={"threads": "metric", "diameter": "8"}),
        Assembly(path="scad/bracket.scad", variables={}),
    ]


def test_get_assemblies_empty_brackets(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_ASSEMBLIES}=scad/main.scad[]\n"
    )
    assemblies = get_assemblies(project_root=project_root)
    assert assemblies == [Assembly(path="scad/main.scad", variables={})]


def test_parse_assembly_no_brackets():
    result = _parse_assembly("scad/main.scad")
    assert result == Assembly(path="scad/main.scad", variables={})


def test_parse_assembly_single_var():
    result = _parse_assembly("scad/main.scad[threads=metric]")
    assert result == Assembly(path="scad/main.scad", variables={"threads": "metric"})


def test_parse_assembly_multiple_vars():
    result = _parse_assembly("scad/main.scad[threads=metric;diameter=8;count=3]")
    assert result == Assembly(
        path="scad/main.scad",
        variables={
            "threads": "metric",
            "diameter": "8",
            "count": "3",
        },
    )


def test_parse_assembly_escaped_semicolon():
    result = _parse_assembly(r"scad/main.scad[path=C:\path\to\file;name=test\;special]")
    assert result == Assembly(
        path="scad/main.scad",
        variables={
            "path": r"C:\path\to\file",
            "name": "test;special",
        },
    )


def test_parse_assembly_escaped_equals():
    result = _parse_assembly(r"scad/main.scad[expr=a\=b]")
    assert result == Assembly(path="scad/main.scad", variables={"expr": "a=b"})


def test_parse_assembly_escaped_backslash():
    result = _parse_assembly(r"scad/main.scad[path=C:\\\\path]")
    assert result == Assembly(path="scad/main.scad", variables={"path": r"C:\\path"})


def test_parse_assembly_missing_closing_bracket():
    with pytest.raises(BuildscadAssemblyParseError, match="Missing closing bracket"):
        _parse_assembly("scad/main.scad[var=value")


def test_parse_assembly_chars_after_bracket():
    with pytest.raises(
        BuildscadAssemblyParseError, match="Unexpected characters after closing bracket"
    ):
        _parse_assembly("scad/main.scad[var=value]extra")


def test_parse_assembly_empty_key():
    with pytest.raises(BuildscadAssemblyParseError, match="Empty variable key"):
        _parse_assembly("scad/main.scad[=value]")


def test_parse_assembly_no_equals_in_var():
    with pytest.raises(BuildscadAssemblyParseError, match="Invalid variable format"):
        _parse_assembly("scad/main.scad[badvar]")


def test_parse_assembly_empty_entry():
    with pytest.raises(BuildscadAssemblyParseError, match="Empty assembly entry"):
        _parse_assembly("")


def test_unescape_value():
    assert _unescape_value(r"hello\;world") == "hello;world"
    assert _unescape_value(r"a\=b") == "a=b"
    assert _unescape_value(r"C:\\path") == r"C:\path"
    assert _unescape_value(r"\\;\=") == r"\;="


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
    with pytest.raises(BuildscadInvalidProperty, match="must contain a JSON array"):
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
    with pytest.raises(BuildscadMissingConfigFile, match="buildscad.properties not found"):
        get_project_root()


def test_load_properties_not_found(project_root):
    with pytest.raises(BuildscadMissingConfigFile, match="buildscad.properties not found"):
        load_properties(project_root)


def test_load_deps_not_found(project_root):
    with pytest.raises(BuildscadMissingConfigFile, match="deps.json not found"):
        load_deps(project_root)


def test_get_output_formats_default(initialized_project):
    formats = get_output_formats(project_root=initialized_project)
    assert formats == [OutputType.STL]


def test_get_output_formats_from_property(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OUTPUT_FORMAT}=3mf\n"
    )
    formats = get_output_formats(project_root=project_root)
    assert formats == [OutputType.THREE_MF]


def test_get_output_formats_multiple(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OUTPUT_FORMAT}=stl,png\n"
    )
    formats = get_output_formats(project_root=project_root)
    assert formats == [OutputType.STL, OutputType.PNG]


def test_get_output_formats_cli_takes_precedence(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OUTPUT_FORMAT}=3mf\n"
    )
    formats = get_output_formats(cli_types=("amf",), project_root=project_root)
    assert formats == [OutputType.AMF]


def test_get_output_formats_cli_multiple(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OUTPUT_FORMAT}=3mf\n"
    )
    formats = get_output_formats(cli_types=("stl", "png"), project_root=project_root)
    assert formats == [OutputType.STL, OutputType.PNG]


def test_get_output_formats_invalid_cli(project_root):
    with pytest.raises(BuildscadInvalidOutputType, match="not a valid output type"):
        get_output_formats(cli_types=("invalid",))


def test_get_output_formats_invalid_property(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OUTPUT_FORMAT}=badformat\n"
    )
    with pytest.raises(BuildscadInvalidOutputType, match="'badformat' is not a valid output type"):
        get_output_formats(project_root=project_root)


def test_sanitize_filename_basic():
    assert _sanitize_filename("metric") == "metric"
    assert _sanitize_filename("8") == "8"


def test_sanitize_filename_replaces_spaces():
    assert _sanitize_filename("hello world") == "hello_world"


def test_sanitize_filename_replaces_slashes():
    assert _sanitize_filename("C:/models") == "C_models"


def test_sanitize_filename_replaces_special_chars():
    assert _sanitize_filename("test@#$%value") == "test_value"


def test_sanitize_filename_collapses_underscores():
    assert _sanitize_filename("a___b") == "a_b"


def test_sanitize_filename_strips_leading_trailing_underscores():
    assert _sanitize_filename("_hello_") == "hello"


def test_assembly_filename_suffix_no_variables():
    assembly = Assembly(path="scad/main.scad", variables={})
    assert assembly.get_filename_suffix() == ""


def test_assembly_filename_suffix_single_variable():
    assembly = Assembly(path="scad/main.scad", variables={"threads": "metric"})
    assert assembly.get_filename_suffix() == "__threads_metric"


def test_assembly_filename_suffix_multiple_variables():
    assembly = Assembly(path="scad/main.scad", variables={"threads": "metric", "diameter": "8"})
    assert assembly.get_filename_suffix() == "__threads_metric__diameter_8"


def test_assembly_filename_suffix_sanitizes_values():
    assembly = Assembly(path="scad/main.scad", variables={"path": "C:/models"})
    assert assembly.get_filename_suffix() == "__path_C_models"


def test_build_output_filename_with_variables(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_ASSEMBLIES}=scad/main.scad[threads=metric;diameter=8]\n"
    )
    assemblies = get_assemblies(project_root=project_root)
    assert assemblies[0].get_filename_suffix() == "__threads_metric__diameter_8"


def test_build_output_filename_no_variables(project_root):
    project_root.joinpath("buildscad.properties").write_text(f"{PROP_ASSEMBLIES}=scad/main.scad\n")
    assemblies = get_assemblies(project_root=project_root)
    assert assemblies[0].get_filename_suffix() == ""


def test_get_property_env_var_override(initialized_project, monkeypatch):
    monkeypatch.setenv(PROP_LOG_LEVEL, "DEBUG")
    assert get_property(PROP_LOG_LEVEL, project_root=initialized_project) == "DEBUG"


def test_get_openscad_path_env_var_override(initialized_project, monkeypatch):
    monkeypatch.setenv(PROP_OPENSCAD_PATH, "/custom/path/openscad")
    assert get_openscad_path(project_root=initialized_project) == "/custom/path/openscad"


def test_get_colorscheme_env_var_override(initialized_project, monkeypatch):
    monkeypatch.setenv(PROP_OPENSCAD_COLORSCHEME, "Metallic")
    assert get_colorscheme(project_root=initialized_project).value == "Metallic"


def test_get_property_env_var_takes_precedence_over_file(initialized_project, monkeypatch):
    initialized_project.joinpath("buildscad.properties").write_text(f"{PROP_LOG_LEVEL}=INFO\n")
    monkeypatch.setenv(PROP_LOG_LEVEL, "DEBUG")
    assert get_property(PROP_LOG_LEVEL, project_root=initialized_project) == "DEBUG"


def test_get_property_env_var_not_allowed(initialized_project, monkeypatch):
    monkeypatch.setenv(PROP_PROJECT, "env-project")
    assert get_property(PROP_PROJECT, project_root=initialized_project) != "env-project"


def test_env_overridable_props_constant():
    assert PROP_LOG_LEVEL in ENV_OVERRIDABLE_PROPS
    assert PROP_OPENSCAD_PATH in ENV_OVERRIDABLE_PROPS
    assert PROP_OPENSCAD_COLORSCHEME in ENV_OVERRIDABLE_PROPS
    assert PROP_PROJECT not in ENV_OVERRIDABLE_PROPS
    assert PROP_VERSION not in ENV_OVERRIDABLE_PROPS
    assert PROP_AUTHOR not in ENV_OVERRIDABLE_PROPS
    assert PROP_ASSEMBLIES not in ENV_OVERRIDABLE_PROPS
    assert PROP_OUTPUT_FORMAT not in ENV_OVERRIDABLE_PROPS
    assert PROP_OPENSCAD_VERSION not in ENV_OVERRIDABLE_PROPS


def test_get_openscad_version_not_set(initialized_project):
    assert get_openscad_version(project_root=initialized_project) is None


def test_get_openscad_version_set(project_root):
    project_root.joinpath("buildscad.properties").write_text(
        f"{PROP_PROJECT}=test\n{PROP_OPENSCAD_VERSION}=2026.06\n"
    )
    assert get_openscad_version(project_root=project_root) == "2026.06"
