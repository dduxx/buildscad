import re
import subprocess

from buildscad.error import BuildscadOpenSCADVersionMismatch


def parse_version(version_str: str) -> tuple[int, ...]:
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


def get_version_comparisons(version_str: str) -> list[tuple[str, tuple[int, ...]]]:
    conditions = version_str.split(",")
    return [_get_version_comparison(cond.strip()) for cond in conditions if cond.strip()]


def _get_version_comparison(version_str: str) -> tuple[str, tuple[int, ...]]:
    stripped = version_str.strip()
    if stripped.startswith(">="):
        return ">=", parse_version(stripped[2:])
    elif stripped.startswith("<="):
        return "<=", parse_version(stripped[2:])
    else:
        return "==", parse_version(stripped)


def get_installed_openscad_version(openscad_path: str) -> str:
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


def check_openscad_version(openscad_path: str, required_version: str, dep_name: str = "") -> None:
    conditions = get_version_comparisons(required_version)
    installed_str = get_installed_openscad_version(openscad_path)
    installed_tuple = parse_version(installed_str)

    display_parts = []
    for cond in required_version.split(","):
        display_parts.append(re.sub(r"^([><]=)", "", cond.strip()))
    required_display = ",".join(display_parts)

    for operator, required_tuple in conditions:
        if operator == ">=":
            if installed_tuple < required_tuple:
                raise BuildscadOpenSCADVersionMismatch(dep_name, required_display, installed_str)
        elif operator == "<=":
            if installed_tuple > required_tuple:
                raise BuildscadOpenSCADVersionMismatch(dep_name, required_display, installed_str)
        else:
            if installed_tuple != required_tuple:
                raise BuildscadOpenSCADVersionMismatch(dep_name, required_display, installed_str)
