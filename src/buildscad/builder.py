import shutil
import subprocess
from pathlib import Path

from buildscad.config import (
    get_openscad_path,
    BUILD_DIR,
    get_colorscheme,
    Assembly,
    get_openscad_version,
    get_imagesize,
)
from buildscad.types import OutputType
from buildscad.error import (
    BuildscadOpenSCADNotFound,
    BuildscadOpenSCADFailed,
    BuildscadAssemblyFileNotFound,
)
from buildscad.version import check_openscad_version
import logging

logger = logging.getLogger("buildscad")


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
        imagesize = get_imagesize(project_root)
        if imagesize:
            cmd.extend(["--imgsize", imagesize])

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
