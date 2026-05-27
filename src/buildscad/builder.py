import subprocess
from pathlib import Path

from buildscad.config import get_openscad_path, BUILD_DIR, get_colorscheme, Assembly
from buildscad.dependencies import get_dependency_paths
from buildscad.types import OutputType
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
    logger.debug(f"Finished building assembly {input_path} -> {output_path}")
    subprocess.run(cmd, check=True, cwd=str(project_root))


def build_all(
    assemblies: list[Assembly], project_root: Path, output_type: OutputType
) -> list[tuple[str, str]]:
    output_dir = project_root.joinpath(BUILD_DIR, output_type.value)
    output_dir.mkdir(parents=True, exist_ok=True)

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
