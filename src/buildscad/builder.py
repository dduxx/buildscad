import re
import subprocess
from pathlib import Path

from buildscad.config import (
    get_openscad_path,
    BUILD_DIR,
    get_colorscheme,
    Assembly,
    get_openscad_version,
)
from buildscad.types import OutputType
from buildscad.error import (
    BuildscadOpenSCADNotFound,
    BuildscadOpenSCADFailed,
    BuildscadAssemblyFileNotFound,
)
import logging

logger = logging.getLogger("buildscad")


def _parse_version(version_str: str) -> tuple[int, ...]:
    cleaned = version_str.strip()
    cleaned = re.sub(r"\s*\(git.*?\)", "", cleaned)
    cleaned = cleaned.replace(".snap", "")
    cleaned = re.sub(r"-RC\d+", "", cleaned)
    cleaned = re.sub(r"\.ci\d+", "", cleaned)
    cleaned = re.sub(r"^([><]=)", "", cleaned)
    cleaned = re.sub(r"^Q", "", cleaned, flags=re.IGNORECASE)

    parts = cleaned.split(".")
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        q_match = re.match(r"^Q?(\d+)$", part, re.IGNORECASE)
        if q_match:
            result.append(int(q_match.group(1)))
        else:
            try:
                result.append(int(part))
            except ValueError:
                raise ValueError(f"Invalid version component '{part}' in '{version_str}'")

    if not result:
        raise ValueError(f"Invalid version string: '{version_str}'")

    return tuple(result)


def _get_version_comparisons(version_str: str) -> list[tuple[str, tuple[int, ...]]]:
    conditions = version_str.split(",")
    return [_get_version_comparison(cond.strip()) for cond in conditions if cond.strip()]


def _get_version_comparison(version_str: str) -> tuple[str, tuple[int, ...]]:
    stripped = version_str.strip()
    if stripped.startswith(">="):
        return ">=", _parse_version(stripped[2:])
    elif stripped.startswith("<="):
        return "<=", _parse_version(stripped[2:])
    else:
        return "==", _parse_version(stripped)


def _get_installed_openscad_version(openscad_path: str) -> str:
    result = subprocess.run(
        [openscad_path, "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    match = re.search(r"OpenSCAD\s+version\s+(.+)", output)
    if not match:
        raise RuntimeError(f"Could not parse OpenSCAD version from output: '{output}'")
    return match.group(1).strip()


def check_openscad_version(openscad_path: str, required_version: str) -> None:
    conditions = _get_version_comparisons(required_version)
    installed_str = _get_installed_openscad_version(openscad_path)
    installed_tuple = _parse_version(installed_str)

    display_parts = []
    for cond in required_version.split(","):
        display_parts.append(re.sub(r"^([><]=)", "", cond.strip()))
    required_display = ",".join(display_parts)

    for operator, required_tuple in conditions:
        if operator == ">=":
            if installed_tuple < required_tuple:
                raise RuntimeError(
                    f"OpenSCAD version mismatch: required {required_display}, found {installed_str}"
                )
        elif operator == "<=":
            if installed_tuple > required_tuple:
                raise RuntimeError(
                    f"OpenSCAD version mismatch: required {required_display}, found {installed_str}"
                )
        else:
            if installed_tuple != required_tuple:
                raise RuntimeError(
                    f"OpenSCAD version mismatch: required {required_display}, found {installed_str}"
                )


def build_assembly(
    input_path: str,
    output_path: str,
    project_root: Path,
    output_type: OutputType,
    variables: dict[str, str] | None = None,
) -> None:
    logger.debug(f"Building assembly {input_path} -> {output_path}")
    openscad = get_openscad_path(project_root)

    openscad_path = Path(openscad)
    if not openscad_path.exists() and openscad_path.name == openscad:
        import shutil

        found = shutil.which(openscad)
        if not found:
            raise BuildscadOpenSCADNotFound(f"OpenSCAD executable not found: {openscad}")

    if not Path(input_path).exists():
        raise BuildscadAssemblyFileNotFound(f"Assembly file not found: {input_path}")

    cmd = [
        openscad,
        "--viewall",
        "--colorscheme",
        get_colorscheme(project_root).value,
    ]

    if output_type == OutputType.PNG:
        cmd.append("--render")

    if variables:
        for name, value in variables.items():
            cmd.extend(["-D", f"{name}={value}"])

    cmd.extend(["-o", output_path, input_path])

    logger.debug(f"Running OpenSCAD: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, cwd=str(project_root), capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else ""
        raise BuildscadOpenSCADFailed(cmd, e.returncode, stderr) from e
    logger.debug(f"Finished building assembly {input_path} -> {output_path}")


def build_all(
    assemblies: list[Assembly], project_root: Path, output_type: OutputType
) -> list[tuple[str, str]]:
    output_dir = project_root.joinpath(BUILD_DIR, output_type.value)
    output_dir.mkdir(parents=True, exist_ok=True)

    openscad = get_openscad_path(project_root)
    required_version = get_openscad_version(project_root)
    if required_version:
        logger.debug(f"Checking OpenSCAD version against requirement: {required_version}")
        check_openscad_version(openscad, required_version)
        logger.debug("OpenSCAD version check passed")

    built = []
    for assembly in assemblies:
        input_path = Path(assembly.path)
        output_name = input_path.stem + assembly.get_filename_suffix() + "." + output_type.value
        output_path = output_dir.joinpath(input_path.parent, output_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        build_assembly(
            str(input_path), str(output_path), project_root, output_type, assembly.variables
        )
        built.append((str(input_path), str(output_path)))

    return built
