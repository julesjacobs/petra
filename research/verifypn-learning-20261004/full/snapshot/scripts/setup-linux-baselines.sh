#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
test "$(uname -s):$(uname -m)" = Linux:x86_64
# Dependencies: GCC/G++16, flex, bison, ninja, cmake, GLPK/GMP development
# libraries, autoconf, automake, libtool, pkg-config, Python3 and system pip.
for tool in gcc-16 g++-16 flex bison ninja cmake autoreconf libtoolize python3; do
    command -v "$tool" >/dev/null
done
python3 -m venv --without-pip vendor/venv
python3 -m pip --python vendor/venv/bin/python install -r scripts/requirements.txt
commit=82206ddcca45ecc497f8ed8eebc169a7c69d3641
if [ ! -d vendor/SMPT-upstream/.git ]; then
    git clone https://github.com/nicolasAmat/SMPT.git vendor/SMPT-upstream
    git -C vendor/SMPT-upstream checkout --detach "$commit"
fi
test "$(git -C vendor/SMPT-upstream rev-parse HEAD)" = "$commit"
test -z "$(git -C vendor/SMPT-upstream status --porcelain --untracked-files=no)"
mkdir -p vendor/tina-linux
archive=vendor/tina-linux/tina-4.0.0-amd64-linux.tgz
if [ ! -f "$archive" ]; then
    curl -fL --retry 2 --max-time 900 https://projects.laas.fr/tina/binaries/tina-4.0.0-amd64-linux.tgz -o "$archive.part"
    mv "$archive.part" "$archive"
fi
echo '5e1cbd7c2e043419037a3d265914042fde795563094f38ddd88b42444d4afa8c  vendor/tina-linux/tina-4.0.0-amd64-linux.tgz' | sha256sum --check
if [ ! -d vendor/tina-linux/tina-4.0.0 ]; then
    tar --warning=no-unknown-keyword -xzf "$archive" -C vendor/tina-linux
fi
if [ ! -d vendor/SMPT-portable ]; then
    python3 scripts/setup-smpt-portable.py
fi
scripts/setup-4ti2.sh
CMAKE_BUILD_PARALLEL_LEVEL=4 scripts/setup-verifypn.sh
vendor/tina-linux/tina-4.0.0/bin/walk -h >/dev/null
vendor/venv/bin/python -c 'import psutil, sexpdata, z3'
