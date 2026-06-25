# buildscad

A build tool for OpenSCAD projects. Manage dependencies, configure assemblies, and build output files in multiple formats from a single CLI.

## Prerequisites

- Python 3.10+
- Git (for downloading dependencies)
- OpenSCAD or OpenSCAD-Nightly (for building output files)

## Installation

Clone the repository first:

```bash
git clone https://github.com/dduxx/buildscad
cd buildscad
```

To install a specific version, checkout the corresponding tag:

```bash
git clone https://github.com/dduxx/buildscad
cd buildscad
git checkout v1.0.0
```

### Option 1: Install in a virtual environment (recommended)

```bash
# Create and activate a pyenv virtual environment
pyenv virtualenv 3.13 buildscad
pyenv activate buildscad

# Install the project
pip install -e .
```

### Option 2: Install globally

```bash
# Install the project system-wide
pip install -e .
```

## Quick Start

```bash
# Initialize a new project
buildscad init
# Or with a custom name (creates a new directory)
buildscad init --name my-project

# Add dependencies to deps.json, then pull them
buildscad pull

# Build assemblies into STL files (default)
buildscad build

# Build assemblies into a different format
buildscad build --type 3mf
```

## Configuration

### `buildscad.properties`

Java-style properties file. All property names use the `BUILDSCAD_` prefix.

| Property | Required | Default | Description |
|----------|----------|---------|-------------|
| `BUILDSCAD_PROJECT` | Yes | `my-project` | Project name |
| `BUILDSCAD_VERSION` | Yes | `1.0.0` | Project version |
| `BUILDSCAD_AUTHOR` | Yes | `me` | Project author |
| `BUILDSCAD_ASSEMBLIES` | Yes | `scad/main.scad` | Comma-separated list of assembly files to build. Each file may optionally specify OpenSCAD variables using `[key=value;key2=value2]` syntax. |
| `BUILDSCAD_LOG_LEVEL` | No | — | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `BUILDSCAD_OPENSCAD_PATH` | No | `openscad` | Path to OpenSCAD executable |
| `BUILDSCAD_OUTPUT_FORMAT` | No | `stl` | Default output format(s), comma-separated: `stl`, `3mf`, `amf`, `off`, `dxf`, `svg`, `png`, `csg`, `echo`, `ast` |
| `BUILDSCAD_OPENSCAD_COLORSCHEME` | No | `Cornfield` | OpenSCAD color scheme: `Cornfield`, `Sunset`, `Metallic`, `Starlight`, `BeforeDawn`, `Nature`, `DeepOcean`, `Solarized` |
| `BUILDSCAD_IMAGESIZE` | No | `1280,720` | PNG export resolution as `width,height`. Only applies when output format includes `png`. |
| `BUILDSCAD_OPENSCAD_VERSION` | No | — | Required OpenSCAD version. Supports exact match (`2021.01`), minimum (`>=2021.01`), maximum (`<=2021.01`), or comma-separated ranges (`>=2021.01,<=2026.06`). If set, the build will fail if the installed OpenSCAD version does not match. |

Optional properties are commented out by default. Uncomment them to use.

### Environment Variable Overrides

The following properties can be overridden by setting environment variables. Environment variables take precedence over values in `buildscad.properties`:

| Environment Variable | Property |
|---------------------|----------|
| `BUILDSCAD_LOG_LEVEL` | `BUILDSCAD_LOG_LEVEL` |
| `BUILDSCAD_OPENSCAD_PATH` | `BUILDSCAD_OPENSCAD_PATH` |
| `BUILDSCAD_OPENSCAD_COLORSCHEME` | `BUILDSCAD_OPENSCAD_COLORSCHEME` |

Example:

```bash
export BUILDSCAD_OPENSCAD_PATH=/opt/openscad-nightly/openscad
export BUILDSCAD_LOG_LEVEL=DEBUG
buildscad build
```

### `deps.json`

A JSON array of dependencies. Each entry specifies a GitHub URL and a git ref (branch or tag):

```json
[
  {
    "url": "https://github.com/rcolyer/threads-scad",
    "ref": "v2.0.0"
  },
  {
    "url": "https://github.com/nophead/NopSCADlib",
    "ref": "master"
  }
]
```

## Commands

| Command | Description |
|---------|-------------|
| `buildscad init [--name NAME]` | Initialize a new project. Creates `buildscad.properties`, `deps.json`, `scad/`, and `.gitignore`. If `--name` is provided, a new directory is created with that name. If omitted, the current working directory is initialized in place and its name is used as the project name. |
| `buildscad pull [--ignore-cache]` | Download dependencies from `deps.json` into `dependencies/`. `--ignore-cache` forces re-download of existing dependencies. |
| `buildscad build [-t TYPE] [-a ASSEMBLY]` | Build all configured assemblies into output files in `build/<type>/`. Defaults to `stl`, or uses `BUILDSCAD_OUTPUT_FORMAT` if set. CLI `--type` takes precedence over the property. Automatically pulls dependencies first. Supported types: `stl`, `3mf`, `amf`, `off`, `dxf`, `svg`, `png`, `csg`, `echo`, `ast`. Multiple `--type` flags can be specified. Use `-a/--assembly` to build specific assemblies instead of all configured assemblies. Multiple `-a` flags and comma-separated values are supported. |
| `buildscad clean [--keep-deps] [--keep-build]` | Remove the `dependencies/` folder and all build output. `--keep-deps` preserves dependencies. `--keep-build` preserves build output. |

## Assembly Variables

You can pass OpenSCAD variables to individual assemblies using bracket syntax in `BUILDSCAD_ASSEMBLIES`:

```properties
BUILDSCAD_ASSEMBLIES=scad/main.scad[threads=metric;diameter=8],scad/bracket.scad
```

Variables are passed to OpenSCAD via the `-D` flag. Each assembly can have its own set of variables. Use `;` to separate multiple variables within the brackets.

### Escaping

If a value contains `;`, `=`, or `\`, escape them with a backslash:

| Escape | Result |
|--------|--------|
| `\;` | `;` |
| `\=` | `=` |
| `\\` | `\` |

Example with escaped characters:

```properties
BUILDSCAD_ASSEMBLIES=scad/main.scad[path=C\:\\models;name=part\;v2]
```

This passes `-D path=C:\models` and `-D name=part;v2` to OpenSCAD.

## Dependency Resolution

Dependencies are stored in the `dependencies/` folder with the naming convention `author:project:ref`, where special characters in the ref are sanitized (e.g., `/` becomes `_`).

If a dependency is itself a buildscad project (has both `buildscad.properties` and `deps.json`), its transitive dependencies are recursively resolved and stored in the top-level `dependencies/` folder. Relative symlinks are created in the sub-dependency's own `dependencies/` folder pointing back to the top-level copies.

Since each dependency's version is part of its directory name, multiple versions of the same library can coexist. Each sub-project uses whatever version it declares.

Circular dependencies are handled via a tracking set that prevents infinite recursion.

## Project Structure

```
my-project/
├── buildscad.properties   # Project configuration
├── deps.json              # Dependency declarations
├── scad/                  # OpenSCAD source files
│   └── main.scad
├── build/                 # Build output (created on first build)
│   ├── stl/
│   │   └── main.stl
│   └── 3mf/
│       └── main.3mf
├── dependencies/          # Downloaded dependencies
│   └── author:project:ref/
└── .gitignore
```

## Development

### Set up the development environment

```bash
# Create and activate a pyenv virtual environment
pyenv virtualenv 3.13 buildscad
pyenv activate buildscad

# Install the project in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
black src/ tests/
```

### Running the CLI during development

```bash
# From the project root
python -m buildscad.cli --help
```
