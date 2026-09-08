#!/usr/bin/env python3
"""Build a flat, hashed, reproducible Brewie procedure release bundle."""

import argparse
import gzip
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_reproducible_tree(archive, root, prefix):
    for path in sorted(root.rglob("*")):
        relative = Path(prefix) / path.relative_to(root)
        info = archive.gettarinfo(str(path), arcname=str(relative))
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mtime = 0
        if path.is_file():
            with path.open("rb") as source:
                archive.addfile(info, source)
        else:
            archive.addfile(info)


def bundled_entrypoints(value):
    if isinstance(value, str):
        return f"programs/{Path(value).name}"
    if isinstance(value, list):
        return [bundled_entrypoints(item) for item in value]
    if isinstance(value, dict):
        return {key: bundled_entrypoints(item) for key, item in value.items()}
    return value


def build(output):
    package = yaml.safe_load((ROOT / "program-package.yml").read_text())
    version = str(package["version"])
    bundle_name = f"{package['name']}-{version}"
    output.mkdir(parents=True, exist_ok=True)
    stage = output / bundle_name
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "programs").mkdir(parents=True)
    (stage / "schemas").mkdir()
    (stage / "contracts").mkdir()
    (stage / "catalog").mkdir()

    sources = [
        *(ROOT / "workflows").glob("*.yml"),
        *(
            path for path in (ROOT / "procedures").rglob("*.yml")
            if ".backups" not in path.parts
        ),
    ]
    seen = set()
    for source in sorted(sources):
        if source.name in seen:
            raise RuntimeError(f"Flat runtime bundle name collision: {source.name}")
        seen.add(source.name)
        shutil.copy2(source, stage / "programs" / source.name)
    for source in sorted((ROOT / "schemas").glob("*.json")):
        shutil.copy2(source, stage / "schemas" / source.name)
    for source in sorted((ROOT / "contracts").glob("*.yml")):
        shutil.copy2(source, stage / "contracts" / source.name)
    for source in sorted((ROOT / "catalog").glob("*.yml")):
        shutil.copy2(source, stage / "catalog" / source.name)

    files = {
        str(path.relative_to(stage)): digest(path)
        for path in sorted(stage.rglob("*")) if path.is_file()
    }
    manifest = {
        "format": 1,
        "name": package["name"],
        "version": version,
        "requires": package["requires"],
        "entrypoints": bundled_entrypoints(package["entrypoints"]),
        "files": files,
    }
    (stage / "bundle-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    archive_path = output / f"{bundle_name}.tar.gz"
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                add_reproducible_tree(archive, stage, bundle_name)
    checksum = digest(archive_path)
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_path.write_text(f"{checksum}  {archive_path.name}\n", encoding="ascii")
    print(archive_path)
    return archive_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    build(args.output.resolve())


if __name__ == "__main__":
    main()
