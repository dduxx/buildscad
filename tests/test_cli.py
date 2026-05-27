from pathlib import Path

from click.testing import CliRunner

from buildscad.cli import cli, init, pull, clean, build
from buildscad.config import (
    PROP_PROJECT,
    PROP_VERSION,
    PROP_AUTHOR,
    PROP_ASSEMBLIES,
    PROP_LOG_LEVEL,
    PROP_OPENSCAD_PATH,
    PROP_OUTPUT_FORMAT,
    DEFAULT_VALUES,
    BUILD_DIR,
)


def test_init_creates_files(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert Path("buildscad.properties").exists()
        assert Path("deps.json").exists()
        assert Path("scad/main.scad").exists()
        assert Path(".gitignore").exists()


def test_init_idempotent(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        log_output.truncate(0)
        log_output.seek(0)
        runner.invoke(cli, ["init"])
        output = log_output.getvalue()
        assert "already initialized" in output


def test_init_gitignore_content(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        content = Path(".gitignore").read_text()
        assert "build/" in content
        assert "dependencies/" in content
        assert "*.swp" in content
        assert "*.swo" in content
        assert "*~" in content
        assert ".DS_Store" in content
        assert "__pycache__/" in content
        assert "*.pyc" in content


def test_init_properties_content(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        content = Path("buildscad.properties").read_text()
        cwd_name = Path.cwd().name
        assert f"{PROP_PROJECT}={cwd_name}" in content
        assert f"{DEFAULT_VALUES[PROP_VERSION]}" in content
        assert f"{DEFAULT_VALUES[PROP_AUTHOR]}" in content
        assert f"{DEFAULT_VALUES[PROP_ASSEMBLIES]}" in content
        assert f"# {PROP_LOG_LEVEL}={DEFAULT_VALUES[PROP_LOG_LEVEL]}" in content
        assert f"# {PROP_OPENSCAD_PATH}={DEFAULT_VALUES[PROP_OPENSCAD_PATH]}" in content


def test_init_with_name_argument(tmp_dir):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(tmp_dir)):
        result = runner.invoke(cli, ["init", "--name", "my-custom-project"])
        assert result.exit_code == 0
        project_dir = Path("my-custom-project")
        assert project_dir.exists()
        assert project_dir.joinpath("buildscad.properties").exists()
        assert project_dir.joinpath("deps.json").exists()
        assert project_dir.joinpath("scad/main.scad").exists()
        assert project_dir.joinpath(".gitignore").exists()
        content = project_dir.joinpath("buildscad.properties").read_text()
        assert f"{PROP_PROJECT}=my-custom-project" in content


def test_init_name_nested_directory(tmp_dir):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(tmp_dir)):
        result = runner.invoke(cli, ["init", "--name", "path/to/my-project"])
        assert result.exit_code == 0
        project_dir = Path("path/to/my-project")
        assert project_dir.exists()
        assert project_dir.joinpath("buildscad.properties").exists()
        content = project_dir.joinpath("buildscad.properties").read_text()
        assert f"{PROP_PROJECT}=my-project" in content


def test_init_main_scad_content(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        content = Path("scad/main.scad").read_text()
        assert content == ""


def test_pull_no_deps(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["pull"])
        output = log_output.getvalue()
        assert "No dependencies to install." in output


def test_clean(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        deps_dir = Path("dependencies")
        deps_dir.mkdir()
        deps_dir.joinpath("fake:dep:v1").mkdir()
        build_dir = Path("build")
        build_dir.joinpath("stl").mkdir(parents=True)
        build_dir.joinpath("stl", "test.stl").write_text("fake stl")
        assert deps_dir.exists()
        assert build_dir.joinpath("stl", "test.stl").exists()

        runner.invoke(cli, ["clean"])
        output = log_output.getvalue()
        assert "Dependencies cleaned." in output
        assert "Finished cleaning build output." in output
        assert not build_dir.joinpath("stl", "test.stl").exists()


def test_clean_keeps_build_when_flag_set(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        deps_dir = Path("dependencies")
        deps_dir.mkdir()
        deps_dir.joinpath("fake:dep:v1").mkdir()
        build_dir = Path("build")
        build_dir.joinpath("stl").mkdir(parents=True)
        build_dir.joinpath("stl", "test.stl").write_text("fake stl")

        runner.invoke(cli, ["clean", "--keep-build"])
        output = log_output.getvalue()
        assert "Dependencies cleaned." in output
        assert "Keeping build output." in output
        assert "Finished cleaning build output." not in output
        assert build_dir.joinpath("stl", "test.stl").exists()


def test_clean_no_deps_folder(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["clean"])
        output = log_output.getvalue()
        assert "Dependencies cleaned." in output


def test_clean_no_build_folder(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["clean"])
        output = log_output.getvalue()
        assert "Finished cleaning build output." in output


def test_build_invalid_type(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["build", "--type", "invalid"])
        assert result.exit_code != 0
        assert "not a valid output type" in str(result.exception)


from unittest.mock import patch


def test_build_valid_type(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        with patch("buildscad.builder.subprocess.run"):
            result = runner.invoke(cli, ["build", "--type", "3mf"])
        assert result.exit_code == 0
        assert "3mf" in result.output


def test_build_multiple_types(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        with patch("buildscad.builder.subprocess.run"):
            result = runner.invoke(cli, ["build", "--type", "stl", "--type", "png"])
        assert result.exit_code == 0
        assert "stl" in result.output
        assert "png" in result.output


def test_build_uses_property_format_when_no_type_flag(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        props = Path("buildscad.properties").read_text()
        Path("buildscad.properties").write_text(props + f"{PROP_OUTPUT_FORMAT}=3mf\n")
        with patch("buildscad.builder.subprocess.run"):
            result = runner.invoke(cli, ["build"])
        assert result.exit_code == 0
        assert "3mf" in result.output
        assert Path("build/3mf/scad/main.3mf").parent.exists()


def test_build_type_flag_overrides_property(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        props = Path("buildscad.properties").read_text()
        Path("buildscad.properties").write_text(props + f"{PROP_OUTPUT_FORMAT}=3mf\n")
        with patch("buildscad.builder.subprocess.run"):
            result = runner.invoke(cli, ["build", "--type", "amf"])
        assert result.exit_code == 0
        assert "amf" in result.output
        assert "3mf" not in result.output


def test_build_multiple_type_flags_override_property(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        props = Path("buildscad.properties").read_text()
        Path("buildscad.properties").write_text(props + f"{PROP_OUTPUT_FORMAT}=3mf\n")
        with patch("buildscad.builder.subprocess.run"):
            result = runner.invoke(cli, ["build", "--type", "stl", "--type", "png"])
        assert result.exit_code == 0
        assert "stl" in result.output
        assert "png" in result.output
        assert "3mf" not in result.output
