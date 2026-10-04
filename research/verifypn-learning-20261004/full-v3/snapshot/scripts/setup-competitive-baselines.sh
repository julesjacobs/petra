#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
commit=82206ddcca45ecc497f8ed8eebc169a7c69d3641
if [ ! -d vendor/SMPT-upstream/.git ]; then
    git clone https://github.com/nicolasAmat/SMPT.git vendor/SMPT-upstream
    git -C vendor/SMPT-upstream checkout --detach "$commit"
fi
test "$(git -C vendor/SMPT-upstream rev-parse HEAD)" = "$commit"
test -z "$(git -C vendor/SMPT-upstream status --porcelain --untracked-files=no)"
if [ "$(uname -s):$(uname -m)" != Darwin:arm64 ]; then
    echo 'This Tina binary pin targets Apple Silicon macOS; use a separately pinned official build on other hosts.' >&2
    exit 1
fi
mkdir -p vendor/tina
archive=vendor/tina/tina-4.0.0-arm64-darwin.dmg
if [ ! -f "$archive" ]; then
    curl -fL --retry 2 --max-time 600 https://projects.laas.fr/tina/binaries/tina-4.0.0-arm64-darwin.dmg -o "$archive.part"
    mv "$archive.part" "$archive"
fi
test "$(shasum -a 256 "$archive" | cut -d ' ' -f 1)" = f393007438d07abe67eb2a781dbc0083321ffade123464a3f34a1f72bf89fc3a
if [ ! -d vendor/tina/nd.app ]; then
    mount_dir=$(mktemp -d -t pvass-tina)
    trap 'hdiutil detach "$mount_dir" >/dev/null 2>&1 || true; rmdir "$mount_dir" 2>/dev/null || true' EXIT
    hdiutil attach -readonly -nobrowse -mountpoint "$mount_dir" "$archive"
    cp -R "$mount_dir/nd.app" vendor/tina/nd.app
fi
vendor/venv/bin/python -c 'import psutil, sexpdata, z3'
vendor/tina/nd.app/Contents/MacOS/bin/reduce -h >/dev/null
printf '%s\n' 'Pinned SMPT and Tina ready. Use vendor/venv/bin/python for resource-tracked benchmarks.'
