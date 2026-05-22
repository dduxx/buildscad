import re
import shutil
import subprocess
from pathlib import Path
import logging
from buildscad.config import DEP_DIR, DEPS_FILE, PROPERTIES_FILE
from buildscad.config import load_deps as config_load_deps

logger = logging.getLogger("buildscad")


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
    return project_root.joinpath(DEP_DIR)


def is_buildscad_project(dep_path: Path) -> bool:
    return dep_path.joinpath(PROPERTIES_FILE).exists() and dep_path.joinpath(DEPS_FILE).exists()


def _create_symlink(dep_path: Path, project_root: Path) -> None:
    sub_dep_dir = dep_path.joinpath(DEP_DIR)
    sub_dep_dir.mkdir(parents=True, exist_ok=True)

    top_deps_dir = get_dependencies_dir(project_root)

    for item in top_deps_dir.iterdir():
        if not item.is_dir() and not item.is_symlink():
            continue

        link_path = sub_dep_dir.joinpath(item.name)
        if link_path.exists() or link_path.is_symlink():
            continue

        relative_path = Path("..").joinpath(item.name)
        link_path.symlink_to(relative_path)
        logger.debug(f"Symlinked {item.name} -> {relative_path}")


def install_dependency(url: str, ref: str, project_root: Path, ignore_cache: bool = False) -> Path:
    logger.debug(f"Installing dependency {url} : {ref}")
    deps_dir = get_dependencies_dir(project_root)
    dep_name = get_dependency_dir_name(url, ref)
    dep_path = deps_dir.joinpath(dep_name)

    if dep_path.exists():
        logger.debug(f"Dependency already exists.")
        if ignore_cache:
            logger.debug(f"Deleting existing dependency.")
            shutil.rmtree(dep_path)
        else:
            return dep_path

    deps_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "clone", "--branch", ref, "--depth", "1", url, str(dep_path)],
        check=True,
        capture_output=True,
    )

    logger.debug(f"Finished installing dependency {url} : {ref}")

    return dep_path


def install_all_dependencies(
    deps: list[dict],
    project_root: Path,
    ignore_cache: bool = False,
    seen: set | None = None,
) -> list[Path]:
    if seen is None:
        seen = set()

    installed = []
    for dep in deps:
        url = dep["url"]
        ref = dep.get("ref", "main")
        key = f"{url}:{ref}"

        if key in seen:
            logger.debug(f"Skipping already processed dependency: {key}")
            continue

        seen.add(key)

        path = install_dependency(url, ref, project_root, ignore_cache)
        installed.append(path)

        if is_buildscad_project(path):
            logger.debug(
                f"Dependency {path.name} is a buildscad project, resolving its dependencies..."
            )
            try:
                sub_deps = config_load_deps(path)
                if sub_deps:
                    sub_installed = install_all_dependencies(
                        sub_deps, project_root, ignore_cache, seen
                    )
                    _create_symlink(path, project_root)
                    installed.extend(sub_installed)
                    logger.debug(f"Finished resolving dependencies for {path.name}")
            except ValueError:
                logger.debug(
                    f"Dependency {path.name} has invalid {DEPS_FILE}, skipping recursive resolution."
                )

    return installed


def clean_dependencies(project_root: Path) -> None:
    deps_dir = get_dependencies_dir(project_root)
    if deps_dir.exists():
        shutil.rmtree(deps_dir)


def get_dependency_paths(project_root: Path) -> list[str]:
    deps_dir = get_dependencies_dir(project_root)
    if not deps_dir.exists():
        return []
    return [str(d) for d in deps_dir.iterdir() if d.is_dir() or d.is_symlink()]
