import functools
import logging
import sys
import traceback
import click
from pathlib import Path
from copy import deepcopy
from datetime import datetime
import shutil
from buildscad.config import (
    write_properties,
    write_deps,
    load_deps,
    get_project_root,
    get_assemblies,
    get_log_level,
    get_output_formats,
    DEFAULT_VALUES,
    PROP_PROJECT,
    PROPERTIES_FILE,
    DEFAULT_MAIN_FILE,
    SCAD_DIR,
    BUILD_DIR,
    GITIGNORE_FILE,
    DEFAULT_GITIGNORE_CONTENTS,
    DEPS_FILE,
)
from buildscad.dependencies import install_all_dependencies, clean_dependencies
from buildscad.builder import build_all
from buildscad.error import BuildscadError, BuildscadMissingConfigFile

logger = logging.getLogger("buildscad")


def handle_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BuildscadError as e:
            logger.error(f"{e.__class__.__name__}: {e.message}")
            logger.debug(traceback.format_exc())
            sys.exit(1)
        except Exception as e:
            logger.error(f"{type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            sys.exit(2)

    return wrapper


class ISOFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"

    def format(self, record):
        timestamp = self.formatTime(record)
        return f"[{timestamp}][{record.levelname}] - {record.getMessage()}"


def configure_logging():
    try:
        level_str = get_log_level()
        if level_str:
            level = getattr(logging, level_str.upper(), logging.INFO)
        else:
            level = logging.INFO
    except BuildscadMissingConfigFile:
        level = logging.INFO

    handler = logging.StreamHandler()
    handler.setFormatter(ISOFormatter())
    logger.setLevel(level)
    logger.addHandler(handler)


@click.group()
def cli():
    """buildscad - A build tool for OpenSCAD projects."""

    configure_logging()


@cli.command()
@click.option(
    "-n",
    "--name",
    required=False,
    help="Optional project name. If no name is provided the name of the current directory is used",
)
@handle_errors
def init(name):
    """Initialize a new buildscad project."""

    if name:
        project_root = Path.cwd().joinpath(name)
        project_root.mkdir(parents=True, exist_ok=True)
        name = project_root.name
    else:
        project_root = Path.cwd()
        name = project_root.name

    if project_root.joinpath(PROPERTIES_FILE).exists():
        logger.warning("buildscad project already initialized.")
        return

    logger.info(f"Initializing buildscad project: {name}")

    properties = deepcopy(DEFAULT_VALUES)
    properties[PROP_PROJECT] = name

    write_properties(properties, project_root)
    logger.debug(f"Created {PROPERTIES_FILE}")

    write_deps([], project_root)
    logger.debug(f"Created {DEPS_FILE}")

    scad_dir = project_root.joinpath(SCAD_DIR)
    scad_dir.mkdir(parents=True, exist_ok=True)
    scad_dir.joinpath(DEFAULT_MAIN_FILE).write_text("")
    logger.debug(f"Created {SCAD_DIR}/{DEFAULT_MAIN_FILE}")

    gitignore = project_root.joinpath(GITIGNORE_FILE)
    gitignore.write_text(DEFAULT_GITIGNORE_CONTENTS)
    logger.debug(f"Created {GITIGNORE_FILE}")

    logger.info(f"Finished initializing buildscad project: {name}")


@cli.command()
@click.option("--ignore-cache", is_flag=True, help="Force re-download of existing dependencies.")
@handle_errors
def pull(ignore_cache):
    """Install project dependencies."""

    project_root = get_project_root()
    deps = load_deps(project_root)

    if not deps:
        logger.info("No dependencies to install.")
        return

    logger.info(f"Installing {len(deps)} dependencies...")
    install_all_dependencies(deps, project_root, ignore_cache)
    logger.info(f"Done installing {len(deps)} dependencies.")


@cli.command()
@click.option("--keep-build", is_flag=True, help="Skip deleting build output files.")
@handle_errors
def clean(keep_build):
    """Clean the project dependencies and build output files."""

    logger.info("Cleaning dependencies.")
    project_root = get_project_root()
    clean_dependencies(project_root)
    logger.info("Dependencies cleaned.")

    if keep_build:
        logger.info("Keeping build output.")
        return

    logger.info("Cleaning build output.")
    build_dir = project_root.joinpath(BUILD_DIR)
    if build_dir.exists():
        for item in build_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
    logger.info("Finished cleaning build output.")


@cli.command()
@click.option(
    "-t",
    "--type",
    "output_types",
    default=None,
    multiple=True,
    help="Output format type. Overrides BUILDSCAD_OUTPUT_FORMAT property. Can be specified multiple times. Valid types: stl, 3mf, amf, off, dxf, svg, png, csg, echo, ast",
)
@handle_errors
def build(output_types):
    """Build assemblies into output files."""

    project_root = get_project_root()

    logger.info(f"Building project {project_root.name}")

    deps = load_deps(project_root)
    if deps:
        logger.info("Installing dependencies...")
        install_all_dependencies(deps, project_root)
        logger.info("Dependencies ready.")

    assemblies = get_assemblies(project_root)
    if not assemblies:
        logger.warning("No assemblies configured.")
        return

    formats = get_output_formats(output_types, project_root)

    for format in formats:
        logger.info(f"Building {len(assemblies)} assemblies as {format.value}...")
        build_all(assemblies, project_root, format)
        logger.info(f"Built {len(assemblies)} assemblies as {format.value}.")


if __name__ == "__main__":
    cli()
