import json
from pathlib import Path

PROP_PROJECT = "BUILDSCAD_PROJECT"
PROP_VERSION = "BUILDSCAD_VERSION"
PROP_AUTHOR = "BUILDSCAD_AUTHOR"
PROP_ASSEMBLIES = "BUILDSCAD_ASSEMBLIES"
PROP_LOG_LEVEL = "BUILDSCAD_LOG_LEVEL"
PROP_OPENSCAD_PATH = "BUILDSCAD_OPENSCAD_PATH"

REQUIRED_PROPS = [PROP_PROJECT, PROP_VERSION, PROP_AUTHOR, PROP_ASSEMBLIES]
OPTIONAL_PROPS = [PROP_LOG_LEVEL, PROP_OPENSCAD_PATH]

DEFAULT_VALUES = {
    PROP_PROJECT: "my-project",
    PROP_VERSION: "1.0.0",
    PROP_AUTHOR: "me",
    PROP_ASSEMBLIES: "scad/main.scad",
    PROP_LOG_LEVEL: "INFO",
    PROP_OPENSCAD_PATH: "/usr/bin/openscad",
}

SCAD_DIR = "scad"
STL_DIR = "stl"
DEP_DIR = "dependencies"

PROPERTIES_FILE = "buildscad.properties"
DEFAULT_MAIN_FILE = "main.scad"
GITIGNORE_FILE = ".gitignore"

DEFAULT_GITIGNORE_CONTENTS = """
stl/
dependencies/
*.swp
*.swo
*~
.DS_Store
__pycache__/
*.pyc
"""


def get_project_root() -> Path:
    root = Path.cwd()
    if not root.joinpath(PROPERTIES_FILE).exists():
        raise FileNotFoundError(
            f"buildscad.properties not found in {root}. Run 'buildscad init' first."
        )
    return root


def load_properties(project_root: Path | None = None) -> dict[str, str]:
    root = project_root or get_project_root()
    props_path = root.joinpath(PROPERTIES_FILE)
    if not props_path.exists():
        raise FileNotFoundError(f"buildscad.properties not found in {root}")

    properties = {}
    with open(props_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                properties[key.strip()] = value.strip()

    return properties


def get_property(
    key: str, default: str | None = None, project_root: Path | None = None
) -> str | None:
    props = load_properties(project_root)
    return props.get(key, default)


def get_openscad_path(project_root: Path | None = None) -> str:
    path = get_property(PROP_OPENSCAD_PATH, project_root=project_root)
    if path:
        return path
    return "openscad"


def get_log_level(project_root: Path | None = None) -> str | None:
    return get_property(PROP_LOG_LEVEL, project_root=project_root)


def get_assemblies(project_root: Path | None = None) -> list[str]:
    assemblies_str = get_property(
        PROP_ASSEMBLIES, DEFAULT_VALUES[PROP_ASSEMBLIES], project_root=project_root
    )
    if assemblies_str is None:
        raise ValueError("Project properties does not contain an assembly property")

    return [a.strip() for a in assemblies_str.split(",") if a.strip()]


def load_deps(project_root: Path | None = None) -> list[dict]:
    root = project_root or get_project_root()
    deps_path = root.joinpath("deps.json")
    if not deps_path.exists():
        raise FileNotFoundError(
            f"deps.json not found in {root} or any parent directory"
        )

    with open(deps_path) as f:
        deps = json.load(f)

    if not isinstance(deps, list):
        raise ValueError("deps.json must contain a JSON array")

    return deps


def write_properties(
    properties: dict[str, str], project_root: Path | None = None
) -> None:
    root = project_root or Path.cwd()
    props_path = root.joinpath(PROPERTIES_FILE)

    lines = []
    for key in REQUIRED_PROPS:
        if key in properties:
            lines.append(f"{key}={properties[key]}")

    for key in OPTIONAL_PROPS:
        if key in properties:
            lines.append(f"# {key}={properties[key]}")

    with open(props_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def write_deps(deps: list[dict], project_root: Path | None = None) -> None:
    root = project_root or Path.cwd()
    deps_path = root / "deps.json"
    with open(deps_path, "w") as f:
        json.dump(deps, f, indent=2)
