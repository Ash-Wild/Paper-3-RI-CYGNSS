"""Generate requirements.txt from imports used in project Python scripts."""

from __future__ import annotations

import ast
import argparse
import importlib.metadata
import pathlib
import sys
from typing import Iterable

DEFAULT_EXCLUDED_DIRS = {".git", ".venv", "__pycache__"}


def iter_python_files(root: pathlib.Path, excluded_dirs: set[str]) -> Iterable[pathlib.Path]:
    for file_path in root.rglob("*.py"):
        if any(part in excluded_dirs for part in file_path.parts):
            continue
        if file_path.name == pathlib.Path(__file__).name:
            continue
        yield file_path


def collect_imported_modules(file_paths: Iterable[pathlib.Path]) -> set[str]:
    imported: set[str] = set()
    for file_path in file_paths:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
    return imported


def local_module_names(root: pathlib.Path, excluded_dirs: set[str]) -> set[str]:
    modules: set[str] = set()
    for file_path in iter_python_files(root, excluded_dirs):
        if file_path.stem != "__init__":
            modules.add(file_path.stem)
    return modules


def generate_requirements(root: pathlib.Path, output_file: pathlib.Path, excluded_dirs: set[str]) -> None:
    imported_modules = collect_imported_modules(iter_python_files(root, excluded_dirs))
    stdlib_modules = set(sys.builtin_module_names) | set(getattr(sys, "stdlib_module_names", set()))
    project_modules = local_module_names(root, excluded_dirs)

    third_party_modules = sorted(
        module
        for module in imported_modules
        if module not in stdlib_modules and module not in project_modules
    )

    package_mapping = importlib.metadata.packages_distributions()

    resolved_packages: set[str] = set()
    unresolved_modules: list[str] = []
    for module in third_party_modules:
        distributions = package_mapping.get(module)
        if not distributions:
            unresolved_modules.append(module)
            continue
        resolved_packages.add(distributions[0])

    requirement_lines: list[str] = [
        "# Auto-generated from Python imports. Run: python sync_requirements.py",
    ]
    for package_name in sorted(resolved_packages, key=str.lower):
        version = importlib.metadata.version(package_name)
        requirement_lines.append(f"{package_name}=={version}")

    if unresolved_modules:
        requirement_lines.append("")
        requirement_lines.append("# Unresolved imports (add and pin manually):")
        requirement_lines.extend(f"# {module}" for module in unresolved_modules)

    output_file.write_text("\n".join(requirement_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync requirements.txt from project imports.")
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent,
        help="Project root directory to scan.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent / "requirements.txt",
        help="Output requirements file.",
    )
    args = parser.parse_args()

    generate_requirements(
        root=args.root.resolve(),
        output_file=args.output.resolve(),
        excluded_dirs=DEFAULT_EXCLUDED_DIRS,
    )
    print(f"Updated requirements file: {args.output.resolve()}")


if __name__ == "__main__":
    main()
