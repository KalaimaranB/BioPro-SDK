import json
from pathlib import Path


def setup_migrate_parser(subparsers):
    # Command: migrate
    migrate_parser = subparsers.add_parser("migrate", help="Migrate a legacy plugin to the new architecture.")
    migrate_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")
    migrate_parser.set_defaults(func=migrate_plugin)


def migrate_plugin(args) -> bool:  # noqa: C901
    """Migrate a legacy plugin to the new architecture (pyproject.toml, src/ layout)."""
    print(f"Migrating legacy plugin at {args.plugin_dir} to new SDK architecture...")

    p_dir = Path(args.plugin_dir)
    manifest_path = p_dir / "manifest.json"

    if not manifest_path.exists():
        print("ERROR: manifest.json not found. This doesn't look like a valid legacy plugin.")
        return False

    with open(manifest_path, encoding="utf-8") as f:
        manifest_data = json.load(f)

    plugin_id = manifest_data.get("id", p_dir.name.lower().replace("-", "_").replace(" ", "_"))

    # 1. Generate pyproject.toml
    print("1. Creating pyproject.toml and deprecating manifest.json...")

    toml_path = p_dir / "pyproject.toml"

    # Extract dependencies
    dependencies_str = ""
    if "python_dependencies" in manifest_data:
        for dep, ver in manifest_data["python_dependencies"].items():
            dependencies_str += f'    "{dep}{ver}",\n'

    # Build authors block for project
    project_authors = ""
    if "authors" in manifest_data:
        for author in manifest_data["authors"]:
            name = author.get("name", "Unknown")
            project_authors += f'    {{ name = "{name}" }},\n'

    # Build authors block for plugin
    plugin_authors = ""
    if "authors" in manifest_data:
        for author in manifest_data["authors"]:
            name = author.get("name", "Unknown")
            role = author.get("role", "Developer")
            perms_str = json.dumps(author.get("permissions", []))
            plugin_authors += f'    {{ name = "{name}", role = "{role}", permissions = {perms_str} }},\n'

    clean_project_authors = project_authors.rstrip(",\\n")
    clean_deps = dependencies_str.rstrip(",\\n")
    clean_plugin_authors = plugin_authors.rstrip(",\\n")
    reqs_json = json.dumps(manifest_data.get("requires", ["task_scheduler", "logger", "event_bus"]))

    toml_content = f'''[project]
name = "{manifest_data.get("name", p_dir.name.title())}"
version = "{manifest_data.get("version", "1.0.0")}"
description = "{manifest_data.get("description", "")}"
readme = "README.md"
requires-python = ">=3.11"
authors = [
{clean_project_authors}
]
dependencies = [
{clean_deps}
]

[tool.biopro.plugin]
id = "{plugin_id}"
min_core_version = "{manifest_data.get("min_core_version", "1.4.9")}"
entry_point = "biopro_plugins.{plugin_id}:initialize"
requires = {reqs_json}
authors = [
{clean_plugin_authors}
]
'''
    with open(toml_path, "w", encoding="utf-8") as f:
        f.write(toml_content)

    print(
        "   -> Renaming manifest.json to manifest.json.deprecated (DO NOT DELETE yet, the core still uses it internally!)"
    )
    manifest_path.rename(p_dir / "manifest.json.deprecated")

    # 2. Setup src structure
    print("2. Restructuring python files into src/...")
    src_dir = p_dir / "src"
    src_dir.mkdir(exist_ok=True)

    plugin_pkg_dir = src_dir / "biopro_plugins" / plugin_id
    plugin_pkg_dir.mkdir(parents=True, exist_ok=True)

    # Move all .py files except setup.py to the new package directory
    py_files_moved = 0
    for file in p_dir.glob("*.py"):
        if file.name not in {"setup.py", "conftest.py"}:
            print(f"   -> Moving {file.name} to {plugin_pkg_dir.relative_to(p_dir)}")
            file.rename(plugin_pkg_dir / file.name)
            py_files_moved += 1

    if py_files_moved == 0:
        # Create an empty __init__.py if no files were moved
        (plugin_pkg_dir / "__init__.py").touch()

    print("\n✅ Migration complete! Please verify your imports in the new src/biopro_plugins/ folder.")
    print("Run 'biopro-sdk sign .' to sign the new structure.")
    return True
