"""Copy installed license notices into the distribution; never copy user data."""
import json
import shutil
import sys
from importlib.metadata import distributions
from pathlib import Path


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    inventory = []
    for dist in sorted(distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = dist.metadata["Name"]
        if name == "klippy-assistant":
            continue
        notices = []
        for file in dist.files or []:
            parts = [p.lower() for p in file.parts]
            if any(p.startswith(("license", "copying", "notice", "copyright")) for p in parts):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = destination / name / file.name
                    # Preserve separate license files that have the same basename.
                    if target.exists() and target.read_bytes() != source.read_bytes():
                        target = target.with_name(str(len(notices)) + "-" + target.name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    notices.append(target.relative_to(destination).as_posix())
        inventory.append({"name": name, "version": dist.version, "license_files": notices,
                          "license_expression": dist.metadata.get("License-Expression", ""),
                          "source": dist.metadata.get("Home-page", "")})
    (destination / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", destination / "PYTHON-LICENSE.txt")
    shutil.copy2("THIRD_PARTY_LICENSES.md", destination / "THIRD_PARTY_LICENSES.md")
    shutil.copytree("packaging/licenses", destination / "additional", dirs_exist_ok=True)


if __name__ == "__main__":
    main()
