import subprocess
from pathlib import Path

from buildscad.config import get_openscad_path
from buildscad.dependencies import get_dependency_paths


def build_assembly(
    input_path: str,
    output_path: str,
    project_root: Path,
) -> None:
    openscad = get_openscad_path(project_root)
    dep_paths = get_dependency_paths(project_root)

    cmd = [openscad, "-o", output_path]
    for dep_path in dep_paths:
        cmd.extend(["-I", dep_path])
    cmd.append(input_path)

    subprocess.run(cmd, check=True, cwd=str(project_root))


def build_all(assemblies: list[str], project_root: Path) -> list[tuple[str, str]]:
    stl_dir = project_root.joinpath("stl")
    stl_dir.mkdir(parents=True, exist_ok=True)

    built = []
    for assembly in assemblies:
        input_path = Path(assembly)
        output_name = input_path.stem + ".stl"
        output_path = stl_dir.joinpath(output_name)

        build_assembly(str(input_path), str(output_path), project_root)
        built.append((str(input_path), str(output_path)))

    return built
