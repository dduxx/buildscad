import json
from pathlib import Path
from jproperties import Properties
from buildscad.types import OutputType, ColorScheme

PROP_PROJECT = "BUILDSCAD_PROJECT"
PROP_VERSION = "BUILDSCAD_VERSION"
PROP_AUTHOR = "BUILDSCAD_AUTHOR"
PROP_ASSEMBLIES = "BUILDSCAD_ASSEMBLIES"
PROP_LOG_LEVEL = "BUILDSCAD_LOG_LEVEL"
PROP_OPENSCAD_PATH = "BUILDSCAD_OPENSCAD_PATH"
PROP_OUTPUT_FORMAT = "BUILDSCAD_OUTPUT_FORMAT"
PROP_OPENSCAD_COLORSCHEME = "BUILDSCAD_OPENSCAD_COLORSCHEME"

REQUIRED_PROPS = [PROP_PROJECT, PROP_VERSION, PROP_AUTHOR, PROP_ASSEMBLIES]
OPTIONAL_PROPS = [
    PROP_LOG_LEVEL,
    PROP_OPENSCAD_PATH,
    PROP_OUTPUT_FORMAT,
    PROP_OPENSCAD_COLORSCHEME,
]

DEFAULT_VALUES = {
    PROP_PROJECT: "my-project",
    PROP_VERSION: "1.0.0",
    PROP_AUTHOR: "me",
    PROP_ASSEMBLIES: "scad/main.scad",
    PROP_LOG_LEVEL: "INFO",
    PROP_OPENSCAD_PATH: "/usr/bin/openscad",
    PROP_OUTPUT_FORMAT: "stl",
    PROP_OPENSCAD_COLORSCHEME: "Cornfield",
}

SCAD_DIR = "scad"
BUILD_DIR = "build"
DEP_DIR = "dependencies"
DEPS_FILE = "deps.json"

PROPERTIES_FILE = "buildscad.properties"
DEFAULT_MAIN_FILE = "main.scad"
GITIGNORE_FILE = ".gitignore"

DEFAULT_GITIGNORE_CONTENTS = """
# buildscad
build/
dependencies/

# Python
__pycache__/
*.pyc
*.pyo

# Editors
*.swp
*.swo
*~
.idea/
.vscode/
*.sublime-*

# OS
.DS_Store
Thumbs.db
"""


def get_project_root() -> Path:
    root = Path.cwd()
    if not root.joinpath(PROPERTIES_FILE).exists():
        raise FileNotFoundError(
            f"{PROPERTIES_FILE} not found in {root}. Run 'buildscad init' first."
        )
    return root


def load_properties(project_root: Path | None = None) -> dict[str, str]:
    root = project_root or get_project_root()
    props_path = root.joinpath(PROPERTIES_FILE)
    if not props_path.exists():
        raise FileNotFoundError(f"{PROPERTIES_FILE} not found in {root}")

    props = Properties()
    with open(props_path, "rb") as f:
        props.load(f)
    return {k: v.data for k, v in props.items()}


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


def get_output_formats(
    cli_types: tuple[str, ...] | None = None, project_root: Path | None = None
) -> list[OutputType]:
    if cli_types:
        return [_parse_output_type(t) for t in cli_types]

    format = get_property(PROP_OUTPUT_FORMAT, project_root=project_root)
    if format:
        return [_parse_output_type(t.strip()) for t in format.split(",") if t.strip()]

    return [OutputType.STL]


def _parse_output_type(value: str) -> OutputType:
    try:
        return OutputType(value)
    except ValueError:
        valid = ", ".join([t.value for t in OutputType])
        raise ValueError(f"'{value}' is not a valid output type. Valid types: {valid}")


def get_colorscheme(project_root: Path | None = None) -> ColorScheme:
    colorscheme = get_property(PROP_OPENSCAD_COLORSCHEME, project_root=project_root)
    if not colorscheme:
        return ColorScheme.CORNFIELD
    try:
        return ColorScheme(colorscheme)
    except ValueError:
        valid = ", ".join([c.value for c in ColorScheme])
        raise ValueError(
            f"Invalid {PROP_OPENSCAD_COLORSCHEME} value '{colorscheme}'. Valid schemes: {valid}"
        )


def get_assemblies(project_root: Path | None = None) -> list[str]:
    assemblies_str = get_property(
        PROP_ASSEMBLIES, DEFAULT_VALUES[PROP_ASSEMBLIES], project_root=project_root
    )
    if assemblies_str is None:
        raise ValueError("Project properties does not contain an assembly property")

    return [a.strip() for a in assemblies_str.split(",") if a.strip()]


def load_deps(project_root: Path | None = None) -> list[dict]:
    if project_root is None:
        project_root = get_project_root()

    deps_path = project_root.joinpath(f"{DEPS_FILE}")

    if not deps_path.exists():
        raise FileNotFoundError(f"{DEPS_FILE} not found in {project_root}.")

    with open(deps_path) as f:
        deps = json.load(f)

    if not isinstance(deps, list):
        raise ValueError(f"{DEPS_FILE} must contain a JSON array")

    return deps


def write_properties(
    properties: dict[str, str], project_root: Path | None = None
) -> None:
    if project_root is None:
        project_root = get_project_root()

    props_path = project_root.joinpath(PROPERTIES_FILE)

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
    if project_root is None:
        project_root = get_project_root()

    deps_path = project_root.joinpath(DEPS_FILE)
    with open(deps_path, "w") as f:
        json.dump(deps, f, indent=2)
