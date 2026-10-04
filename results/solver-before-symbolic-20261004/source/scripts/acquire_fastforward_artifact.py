#!/usr/bin/env python3
"""Acquire and identify the published archive without extracting or running it."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

METADATA_URL = "https://api.figshare.com/v2/articles/13573592/versions/1"
DOWNLOAD_URL = "https://ndownloader.figshare.com/files/26048870"
SIZE = 960594789
MD5 = "78521fa06a5b88257b42d4bb519dce35"
SHA256 = "3424e0285729df073756e7947b710b3b7f55eb0d396d9781f32d5ad6872dd65f"


def preserve(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"refusing to overwrite differing file: {path}")
    else:
        with path.open("xb") as output:
            output.write(data)


def identify(path):
    md5, sha256, size = hashlib.md5(), hashlib.sha256(), 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            size += len(block)
            md5.update(block)
            sha256.update(block)
    if size != SIZE or md5.hexdigest() != MD5 or sha256.hexdigest() != SHA256:
        raise RuntimeError(f"archive identity mismatch; preserved {path}: size={size}, md5={md5.hexdigest()}, sha256={sha256.hexdigest()}")
    return {"bytes": size, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("vendor/FastForward-artifact-v1"))
    args = parser.parse_args()
    root = args.directory
    root.mkdir(parents=True, exist_ok=True)
    metadata_path = root / "figshare-version-1.json"
    if metadata_path.exists():
        raw_metadata = metadata_path.read_bytes()
    else:
        with urllib.request.urlopen(METADATA_URL, timeout=60) as response:
            raw_metadata = response.read()
        preserve(metadata_path, raw_metadata)
    metadata = json.loads(raw_metadata)
    if (metadata.get("id"), metadata.get("version")) != (13573592, 1):
        raise RuntimeError("unexpected article/version")
    files = [entry for entry in metadata["files"] if entry["id"] == 26048870]
    if len(files) != 1:
        raise RuntimeError("missing or ambiguous archive identity")
    entry = files[0]
    if (entry["name"], entry["size"], entry["computed_md5"], entry["download_url"]) != (
        "FastForward.zip", SIZE, MD5, DOWNLOAD_URL
    ):
        raise RuntimeError("upstream metadata differs from the pinned artifact")
    archive = root / "FastForward.zip"
    if not archive.exists():
        partial = root / "FastForward.zip.partial"
        with partial.open("xb") as output, urllib.request.urlopen(DOWNLOAD_URL, timeout=60) as response:
            size, report = 0, 128 * 1024 * 1024
            for block in iter(lambda: response.read(1024 * 1024), b""):
                output.write(block)
                size += len(block)
                if size > SIZE:
                    raise RuntimeError("archive exceeds expected size; partial file preserved")
                if size >= report:
                    print(f"downloaded {size}/{SIZE} bytes", flush=True)
                    report += 128 * 1024 * 1024
        identify(partial)
        # Link creation refuses to replace an archive that appeared concurrently.
        archive.hardlink_to(partial)
        partial.unlink()
    identity = identify(archive)
    with zipfile.ZipFile(archive) as source:
        entries = [{"path": item.filename, "bytes": item.file_size,
                    "compressed_bytes": item.compress_size, "crc32": f"{item.CRC:08x}",
                    "compression": item.compress_type, "external_attr": item.external_attr}
                   for item in source.infolist()]
    directory = json.dumps(entries, indent=2, sort_keys=True).encode() + b"\n"
    preserve(root / "zip-directory.json", directory)
    manifest_path = root / "acquisition.json"
    manifest = {
        "metadata_url": METADATA_URL,
        "download_url": DOWNLOAD_URL,
        "doi": metadata["doi"],
        "license": metadata["license"],
        "metadata_sha256": hashlib.sha256(raw_metadata).hexdigest(),
        "archive": {"path": archive.name, **identity},
        "zip_directory_sha256": hashlib.sha256(directory).hexdigest(),
        "zip_entries": len(entries),
        "extracted": False,
    }
    preserve(manifest_path, json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
