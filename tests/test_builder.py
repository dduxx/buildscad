import subprocess
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

import pytest

from buildscad.builder import build_assembly, build_all
from buildscad.config import Assembly
from buildscad.types import OutputType
from buildscad.error import (
    BuildscadOpenSCADNotFound,
    BuildscadAssemblyFileNotFound,
    BuildscadOpenSCADFailed,
    BuildscadOpenSCADVersionMismatch,
)

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
    assert "--imgsize" in cmd
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
        build_all(assemblies, tmp_path, [OutputType.STL])

    assert (tmp_path / "build" / "stl").exists()


def test_build_all_multi_format(tmp_path):
    props = tmp_path.joinpath("buildscad.properties")
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path.joinpath("scad", "main.scad")
    scad_file.parent.mkdir()
    scad_file.touch()

    with patch("buildscad.builder.subprocess.run"):
        assemblies = [Assembly(path=str(scad_file), variables={})]
        build_all(assemblies, tmp_path, [OutputType.STL, OutputType.THREE_MF])

    assert tmp_path.joinpath("build", "stl").exists()
    assert tmp_path.joinpath("build", "3mf").exists()


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
        build_all(assemblies, tmp_path, [OutputType.STL])

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
            build_all(assemblies, tmp_path, [OutputType.STL])


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
                build_all(assemblies, tmp_path, [OutputType.STL])


def test_build_all_threaded_uses_thread_pool(tmp_path):
    props = tmp_path.joinpath("buildscad.properties")
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path.joinpath("scad", "main.scad")
    scad_file.parent.mkdir()
    scad_file.touch()

    with patch("buildscad.builder.subprocess.run"):
        with patch("buildscad.builder.ThreadPoolExecutor", wraps=ThreadPoolExecutor) as mock_pool:
            assemblies = [Assembly(path=str(scad_file), variables={})]
            build_all(assemblies, tmp_path, [OutputType.STL, OutputType.THREE_MF], threads=2)

        mock_pool.assert_called_once_with(max_workers=2)


def test_build_all_threaded_exception_cancels_remaining(tmp_path):
    props = tmp_path.joinpath("buildscad.properties")
    props.write_text("BUILDSCAD_PROJECT=test\nBUILDSCAD_OPENSCAD_PATH=/usr/bin/openscad\n")
    scad_file = tmp_path.joinpath("scad", "main.scad")
    scad_file.parent.mkdir()
    scad_file.touch()

    call_count = [0]

    def mock_run_fails_after_first(cmd, **kwargs):
        call_count[0] += 1
        if call_count[0] > 1:
            raise subprocess.CalledProcessError(1, cmd, stderr=b"fail")

    with patch("buildscad.builder.subprocess.run", side_effect=mock_run_fails_after_first):
        assemblies = [Assembly(path=str(scad_file), variables={})]
        with pytest.raises(BuildscadOpenSCADFailed, match="fail"):
            build_all(assemblies, tmp_path, [OutputType.STL, OutputType.THREE_MF], threads=2)
