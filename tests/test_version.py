from unittest.mock import patch, MagicMock

import pytest

from buildscad.version import (
    parse_version,
    _get_version_comparison,
    get_version_comparisons,
    get_installed_openscad_version,
    check_openscad_version,
)
from buildscad.error import BuildscadOpenSCADVersionMismatch

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
