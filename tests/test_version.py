import subprocess
from unittest.mock import patch, MagicMock

import pytest

from buildscad.version import (
    parse_version,
    _get_version_comparison,
    get_version_comparisons,
    get_installed_openscad_version,
    check_openscad_version,
)
from buildscad.error import BuildscadOpenSCADVersionMismatch, BuildscadOpenSCADFailed
from pathlib import Path
from buildscad.builder import build_assembly, build_all
from buildscad.config import Assembly
from buildscad.types import OutputType
from buildscad.error import BuildscadOpenSCADNotFound, BuildscadAssemblyFileNotFound

# ---------------------------------------------------------------------------
# parse_version
# ---------------------------------------------------------------------------


def test_parse_version_basic():
    assert parse_version("2021.01") == (2021, 1)
    assert parse_version("2026.06.12") == (2026, 6, 12)


def test_parse_version_snapshot():
    assert parse_version("2026.06.12.snap") == (2026, 6, 12)


def test_parse_version_rc():
    assert parse_version("2021.01-RC3") == (2021, 1)


def test_parse_version_ci():
    assert parse_version("2021.01.15.ci6794") == (2021, 1, 15)


def test_parse_version_git():
    assert parse_version("2021.01.15 (git abc123)") == (2021, 1, 15)


def test_parse_version_quarter():
    assert parse_version("2024.Q3") == (2024, 3)


def test_parse_version_with_comparison_operators():
    assert parse_version(">=2021.01") == (2021, 1)
    assert parse_version("<=2026.06") == (2026, 6)


def test_parse_version_invalid():
    with pytest.raises(ValueError, match="Invalid version component"):
        parse_version("abc.def")


def test_parse_version_empty():
    with pytest.raises(ValueError, match="Invalid version string"):
        parse_version("")


# ---------------------------------------------------------------------------
# _get_version_comparison
# ---------------------------------------------------------------------------


def test_get_version_comparison_exact():
    op, ver = _get_version_comparison("2021.01")
    assert op == "=="
    assert ver == (2021, 1)


def test_get_version_comparison_gte():
    op, ver = _get_version_comparison(">=2021.01")
    assert op == ">="
    assert ver == (2021, 1)


def test_get_version_comparison_lte():
    op, ver = _get_version_comparison("<=2026.06")
    assert op == "<="
    assert ver == (2026, 6)


# ---------------------------------------------------------------------------
# get_version_comparisons
# ---------------------------------------------------------------------------


def test_get_version_comparisons_single():
    conditions = get_version_comparisons(">=2021.01")
    assert len(conditions) == 1
    assert conditions[0] == (">=", (2021, 1))


def test_get_version_comparisons_range():
    conditions = get_version_comparisons(">=2021.01,<=2026.06")
    assert len(conditions) == 2
    assert conditions[0] == (">=", (2021, 1))
    assert conditions[1] == ("<=", (2026, 6))


def test_get_version_comparisons_with_spaces():
    conditions = get_version_comparisons(">=2021.01, <=2026.06")
    assert len(conditions) == 2
    assert conditions[0] == (">=", (2021, 1))
    assert conditions[1] == ("<=", (2026, 6))


# ---------------------------------------------------------------------------
# get_installed_openscad_version
# ---------------------------------------------------------------------------


def test_get_installed_openscad_version():
    mock_result = MagicMock()
    mock_result.stdout = "OpenSCAD version 2026.06.12.snap\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        version = get_installed_openscad_version("/usr/bin/openscad")
        assert version == "2026.06.12.snap"
        mock_run.assert_called_once_with(
            ["/usr/bin/openscad", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )


def test_get_installed_openscad_version_stderr():
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "OpenSCAD version 2026.06.12.snap\n"
    with patch("subprocess.run", return_value=mock_result):
        version = get_installed_openscad_version("/usr/bin/openscad")
        assert version == "2026.06.12.snap"


def test_get_installed_openscad_version_nightly():
    mock_result = MagicMock()
    mock_result.stdout = "OpenSCAD version 2026.06.12.snap\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        version = get_installed_openscad_version("/usr/bin/openscad-nightly")
        assert version == "2026.06.12.snap"


def test_get_installed_openscad_version_parse_error():
    mock_result = MagicMock()
    mock_result.stdout = "some random output\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Could not parse OpenSCAD version"):
            get_installed_openscad_version("/usr/bin/openscad")


# ---------------------------------------------------------------------------
# check_openscad_version
# ---------------------------------------------------------------------------


def test_check_openscad_version_exact_match():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2021.01"):
        check_openscad_version("/usr/bin/openscad", "2021.01")


def test_check_openscad_version_exact_mismatch():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2021.02"):
        with pytest.raises(BuildscadOpenSCADVersionMismatch, match="OpenSCAD version mismatch"):
            check_openscad_version("/usr/bin/openscad", "2021.01")


def test_check_openscad_version_gte_pass():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2026.06.12.snap"):
        check_openscad_version("/usr/bin/openscad", ">=2021.01")


def test_check_openscad_version_gte_fail():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2020.12"):
        with pytest.raises(
            BuildscadOpenSCADVersionMismatch, match="requires 2021.01, found 2020.12"
        ):
            check_openscad_version("/usr/bin/openscad", ">=2021.01")


def test_check_openscad_version_lte_pass():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2021.01"):
        check_openscad_version("/usr/bin/openscad", "<=2021.01")


def test_check_openscad_version_lte_fail():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2026.06.12.snap"):
        with pytest.raises(
            BuildscadOpenSCADVersionMismatch, match="requires 2021.01, found 2026.06.12.snap"
        ):
            check_openscad_version("/usr/bin/openscad", "<=2021.01")


def test_check_openscad_version_snapshot_gte():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2026.06.12.snap"):
        check_openscad_version("/usr/bin/openscad", ">=2026.06")


def test_check_openscad_version_snapshot_exact_fails():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2026.06.12.snap"):
        with pytest.raises(
            BuildscadOpenSCADVersionMismatch, match="requires 2026.06, found 2026.06.12.snap"
        ):
            check_openscad_version("/usr/bin/openscad", "2026.06")


def test_check_openscad_version_range_pass():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2021.01"):
        check_openscad_version("/usr/bin/openscad", ">=2021.01,<=2021.01")


def test_check_openscad_version_range_pass_middle():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2023.06"):
        check_openscad_version("/usr/bin/openscad", ">=2021.01,<=2026.06")


def test_check_openscad_version_range_fail_lower():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2020.12"):
        with pytest.raises(
            BuildscadOpenSCADVersionMismatch, match="requires 2021.01,2026.06, found 2020.12"
        ):
            check_openscad_version("/usr/bin/openscad", ">=2021.01,<=2026.06")


def test_check_openscad_version_range_fail_upper():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2026.06.12.snap"):
        with pytest.raises(
            BuildscadOpenSCADVersionMismatch,
            match="requires 2021.01,2026.06, found 2026.06.12.snap",
        ):
            check_openscad_version("/usr/bin/openscad", ">=2021.01,<=2026.06")


def test_check_openscad_version_nightly_range():
    with patch("buildscad.version.get_installed_openscad_version", return_value="2026.06.12.snap"):
        check_openscad_version("/usr/bin/openscad", ">=2026.06,<=2026.07")


# ---------------------------------------------------------------------------
# build_assembly
# ---------------------------------------------------------------------------


def test_build_assembly_openscad_not_found(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=nonexistent_openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()
    with patch("shutil.which", return_value=None):
        with patch("buildscad.builder.subprocess.run"):
            with pytest.raises(BuildscadOpenSCADNotFound, match="OpenSCAD executable not found"):
                build_assembly(str(scad_file), "build/main.stl", tmp_path, OutputType.STL)


def test_build_assembly_file_not_found(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    with patch("buildscad.builder.subprocess.run"):
        with pytest.raises(BuildscadAssemblyFileNotFound, match="Assembly file not found"):
            build_assembly("nonexistent.scad", "build/main.stl", tmp_path, OutputType.STL)


def test_build_assembly_calls_openscad(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    captured = []

    def mock_run(cmd, **kwargs):
        captured.append((cmd, kwargs))

    with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
        build_assembly(str(scad_file), "build/main.stl", tmp_path, OutputType.STL)

    assert len(captured) == 1
    cmd, kwargs = captured[0]
    assert cmd[0] == "/usr/bin/openscad"
    assert "--viewall" in cmd
    assert "--colorscheme" in cmd
    assert "Cornfield" in cmd
    assert "-o" in cmd
    assert "build/main.stl" in cmd
    assert str(scad_file) in cmd


def test_build_assembly_passes_variables(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    captured = []

    def mock_run(cmd, **kwargs):
        captured.append(cmd)

    with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
        build_assembly(
            str(scad_file),
            "build/main.stl",
            tmp_path,
            OutputType.STL,
            variables={"threads": "metric", "diameter": "8"},
        )

    cmd = captured[0]
    d_indices = [i for i, x in enumerate(cmd) if x == "-D"]
    assert len(d_indices) == 2
    assert cmd[d_indices[0] + 1] == "threads=metric"
    assert cmd[d_indices[1] + 1] == "diameter=8"


def test_build_assembly_png_adds_render_flag(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    captured = []

    def mock_run(cmd, **kwargs):
        captured.append(cmd)

    with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
        build_assembly(str(scad_file), "build/main.png", tmp_path, OutputType.PNG)

    cmd = captured[0]
    assert "--render" in cmd


def test_build_assembly_png_adds_imagesize(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    captured = []

    def mock_run(cmd, **kwargs):
        captured.append(cmd)

    with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
        build_assembly(str(scad_file), "build/main.png", tmp_path, OutputType.PNG)

    cmd = captured[0]
    assert "--imagesize" in cmd
    assert "1280,720" in cmd


def test_build_assembly_openscad_failed(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    error = subprocess.CalledProcessError(1, ["openscad"], stderr=b"parse error")
    with patch("buildscad.builder.subprocess.run", side_effect=error):
        with pytest.raises(BuildscadOpenSCADFailed, match="parse error"):
            build_assembly(str(scad_file), "build/main.stl", tmp_path, OutputType.STL)


# ---------------------------------------------------------------------------
# build_all
# ---------------------------------------------------------------------------


def test_build_all_creates_output_dir(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    with patch("buildscad.builder.subprocess.run"):
        assemblies = [Assembly(path=str(scad_file), variables={})]
        build_all(assemblies, tmp_path, OutputType.STL)

    assert (tmp_path / "build" / "stl").exists()


def test_build_all_returns_built_list(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    with patch("buildscad.builder.subprocess.run"):
        assemblies = [Assembly(path=str(scad_file), variables={})]
        built = build_all(assemblies, tmp_path, OutputType.STL)

    assert len(built) == 1
    assert built[0][0] == str(scad_file)
    assert built[0][1].endswith("main.stl")


def test_build_all_with_variables(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    captured = []

    def mock_run(cmd, **kwargs):
        captured.append(cmd)

    with patch("buildscad.builder.subprocess.run", side_effect=mock_run):
        assemblies = [Assembly(path=str(scad_file), variables={"threads": "metric"})]
        build_all(assemblies, tmp_path, OutputType.STL)

    cmd = captured[0]
    d_idx = cmd.index("-D")
    assert cmd[d_idx + 1] == "threads=metric"


def test_build_all_version_check_when_set(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text(
        "BUILDSCAD_PROJECT=test\n"
        "BUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n"
        "BUILDSCAD_OPENSCAD_VERSION=>=2021.01\n"
    )
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    with patch("buildscad.builder.subprocess.run"):
        with patch("buildscad.version.get_installed_openscad_version", return_value="2022.01"):
            assemblies = [Assembly(path=str(scad_file), variables={})]
            build_all(assemblies, tmp_path, OutputType.STL)


def test_build_all_version_check_fails(tmp_path):
    props = tmp_path / "buildscad.properties"
    props.write_text(
        "BUILDSCAD_PROJECT=test\n"
        "BUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n"
        "BUILDSCAD_OPENSCAD_VERSION=>=2023.01\n"
    )
    scad_file = tmp_path / "scad" / "main.scad"
    scad_file.parent.mkdir()
    scad_file.touch()

    with patch("buildscad.builder.subprocess.run"):
        with patch("buildscad.version.get_installed_openscad_version", return_value="2021.01"):
            with pytest.raises(BuildscadOpenSCADVersionMismatch):
                assemblies = [Assembly(path=str(scad_file), variables={})]
                build_all(assemblies, tmp_path, OutputType.STL)
