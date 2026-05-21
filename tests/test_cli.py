from pathlib import Path

from click.testing import CliRunner

from buildscad.cli import cli, init, pull, clean
from buildscad.config import (
    PROP_PROJECT,
    PROP_VERSION,
    PROP_AUTHOR,
    PROP_ASSEMBLIES,
    PROP_LOG_LEVEL,
    PROP_OPENSCAD_PATH,
    DEFAULT_VALUES,
)


def test_init_creates_files(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert Path("buildscad.properties").exists()
        assert Path("deps.json").exists()
        assert Path("scad/main.scad").exists()
        assert Path("stl").is_dir()
        assert Path(".gitignore").exists()


def test_init_output_messages(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        output = log_output.getvalue()
        assert "Created buildscad.properties" in output
        assert "Created deps.json" in output
        assert "Created scad/main.scad" in output
        assert "Created stl/" in output
        assert "Created .gitignore" in output
        assert "Project initialized successfully." in output


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
        assert "stl/" in content
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
        assert project_dir.joinpath("stl").is_dir()
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
        assert deps_dir.exists()

        runner.invoke(cli, ["clean"])
        output = log_output.getvalue()
        assert deps_dir.exists()
        assert len(list(deps_dir.iterdir())) == 0
        assert "Dependencies cleaned." in output


def test_clean_no_deps_folder(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["clean"])
        output = log_output.getvalue()
        assert "Dependencies cleaned." in output
