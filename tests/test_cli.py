from pathlib import Path

from click.testing import CliRunner

from buildscad.cli import cli
from buildscad.config import (
    PROP_PROJECT,
    PROP_VERSION,
    PROP_AUTHOR,
    PROP_ASSEMBLIES,
    PROP_LOG_LEVEL,
    PROP_OPENSCAD_PATH,
    PROP_OUTPUT_FORMAT,
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


def test_build_invalid_type(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["build", "--type", "invalid"])
        assert result.exit_code != 0
        output = log_output.getvalue()
        assert "BuildscadInvalidOutputType" in output
        assert "not a valid output type" in output


from unittest.mock import patch


def test_build_valid_type(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        with patch("buildscad.builder.subprocess.run"):
            with patch("shutil.which", return_value="/usr/bin/openscad"):
                result = runner.invoke(cli, ["build", "--type", "3mf"])
        assert result.exit_code == 0
        assert "3mf" in result.output


def test_build_multiple_types(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        with patch("buildscad.builder.subprocess.run"):
            with patch("shutil.which", return_value="/usr/bin/openscad"):
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
            with patch("shutil.which", return_value="/usr/bin/openscad"):
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
            with patch("shutil.which", return_value="/usr/bin/openscad"):
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
            with patch("shutil.which", return_value="/usr/bin/openscad"):
                result = runner.invoke(cli, ["build", "--type", "stl", "--type", "png"])
        assert result.exit_code == 0
        assert "stl" in result.output
        assert "png" in result.output
        assert "3mf" not in result.output


def test_build_with_assembly_variables(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        props = Path("buildscad.properties").read_text()
        Path("buildscad.properties").write_text(
            props + f"{PROP_ASSEMBLIES}=scad/main.scad[threads=metric;diameter=8]\n"
        )
        captured_calls = []

        def mock_run(*args, **kwargs):
            captured_calls.append(args[0])

        with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
            with patch("shutil.which", return_value="/usr/bin/openscad"):
                result = runner.invoke(cli, ["build", "--type", "stl"])
        assert result.exit_code == 0
        assert len(captured_calls) == 1
        cmd = captured_calls[0]
        assert "-D" in cmd
        threads_idx = cmd.index("-D")
        assert cmd[threads_idx + 1] == "threads=metric"
        diameter_idx = cmd.index("-D", threads_idx + 1)
        assert cmd[diameter_idx + 1] == "diameter=8"


def test_build_assembly_no_variables(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        captured_calls = []

        def mock_run(*args, **kwargs):
            captured_calls.append(args[0])

        with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
            with patch("shutil.which", return_value="/usr/bin/openscad"):
                result = runner.invoke(cli, ["build", "--type", "stl"])
        assert result.exit_code == 0
        assert len(captured_calls) == 1
        cmd = captured_calls[0]
        assert "-D" not in cmd


def test_build_output_filename_with_variables(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        props = Path("buildscad.properties").read_text()
        Path("buildscad.properties").write_text(
            props + f"{PROP_ASSEMBLIES}=scad/main.scad[threads=metric;diameter=8]\n"
        )
        captured_calls = []

        def mock_run(*args, **kwargs):
            captured_calls.append((args[0], kwargs))

        with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
            with patch("shutil.which", return_value="/usr/bin/openscad"):
                result = runner.invoke(cli, ["build", "--type", "stl"])
        assert result.exit_code == 0
        assert len(captured_calls) == 1
        cmd = captured_calls[0][0]
        output_idx = cmd.index("-o")
        assert "main__threads_metric__diameter_8.stl" in cmd[output_idx + 1]
        assert Path(cmd[output_idx + 1]).parent.exists()


def test_build_output_filename_without_variables(project_root):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        captured_calls = []

        def mock_run(*args, **kwargs):
            captured_calls.append((args[0], kwargs))

        with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
            with patch("shutil.which", return_value="/usr/bin/openscad"):
                result = runner.invoke(cli, ["build", "--type", "stl"])
        assert result.exit_code == 0
        assert len(captured_calls) == 1
        cmd = captured_calls[0][0]
        output_idx = cmd.index("-o")
        output_path = Path(cmd[output_idx + 1])
        assert output_path.name == "main.stl"


def test_buildscad_error_logs_message_at_error_level(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["build", "--type", "invalid"])
        assert result.exit_code == 1
        output = log_output.getvalue()
        assert "[ERROR]" in output
        assert "BuildscadInvalidOutputType" in output
        assert "not a valid output type" in output


def test_buildscad_error_no_traceback_at_info_level(project_root, log_output):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["build", "--type", "invalid"])
        output = log_output.getvalue()
        assert "Traceback" not in output


def test_unexpected_error_logs_type_and_traceback(project_root, log_output):
    from unittest.mock import patch

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(project_root)):
        runner.invoke(cli, ["init"])

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("something went wrong")

        with patch("buildscad.cli.get_project_root", side_effect=raise_unexpected):
            result = runner.invoke(cli, ["build"])
        assert result.exit_code == 2
        output = log_output.getvalue()
        assert "[ERROR]" in output
        assert "RuntimeError" in output
        assert "something went wrong" in output
