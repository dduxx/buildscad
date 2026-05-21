import re
import shutil
import subprocess
from pathlib import Path

DEPENDENCIES_DIR = "dependencies"


def sanitize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


def parse_github_url(url: str) -> tuple[str, str]:
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    if url.startswith("https://github.com/"):
        path = url[len("https://github.com/") :]
    elif url.startswith("git@github.com:"):
        path = url[len("git@github.com:") :]
    else:
        raise ValueError(f"Unsupported GitHub URL: {url}")

    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}")

    author = parts[0]
    project = parts[1]
    return author, project


def get_dependency_dir_name(url: str, ref: str) -> str:
    author, project = parse_github_url(url)
    sanitized_ref = sanitize_name(ref)
    return f"{sanitize_name(author)}:{sanitize_name(project)}:{sanitized_ref}"


def get_dependencies_dir(project_root: Path) -> Path:
    return project_root.joinpath(DEPENDENCIES_DIR)


def install_dependency(
    url: str, ref: str, project_root: Path, ignore_cache: bool = False
) -> Path:
    deps_dir = get_dependencies_dir(project_root)
    dep_name = get_dependency_dir_name(url, ref)
    dep_path = deps_dir.joinpath(dep_name)

    if dep_path.exists():
        if ignore_cache:
            shutil.rmtree(dep_path)
        else:
            return dep_path

    deps_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "clone", "--branch", ref, "--depth", "1", url, str(dep_path)],
        check=True,
        capture_output=True,
    )

    return dep_path


def install_all_dependencies(
    deps: list[dict], project_root: Path, ignore_cache: bool = False
) -> list[Path]:
    installed = []
    for dep in deps:
        url = dep["url"]
        ref = dep.get("ref", "main")
        path = install_dependency(url, ref, project_root, ignore_cache)
        installed.append(path)
    return installed


def clean_dependencies(project_root: Path) -> None:
    deps_dir = get_dependencies_dir(project_root)
    if deps_dir.exists():
        shutil.rmtree(deps_dir)


def get_dependency_paths(project_root: Path) -> list[str]:
    deps_dir = get_dependencies_dir(project_root)
    if not deps_dir.exists():
        return []
    return [str(d) for d in deps_dir.iterdir() if d.is_dir()]
