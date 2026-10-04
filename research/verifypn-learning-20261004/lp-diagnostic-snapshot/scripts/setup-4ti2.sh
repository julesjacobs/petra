#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
commit=f93eb8e419322a9ce653a6285f3febdbb2f24da4
if [ ! -d vendor/4ti2/.git ]; then
    git clone https://github.com/4ti2/4ti2.git vendor/4ti2
    git -C vendor/4ti2 checkout --detach "$commit"
fi
test "$(git -C vendor/4ti2 rev-parse HEAD)" = "$commit"
prefix="$(pwd)/vendor/4ti2-install"
if [ -x "$prefix/bin/qsolve" ]; then
    "$prefix/bin/qsolve" --version
    exit 0
fi
if [ "$(uname -s)" = Darwin ]; then
    brew install glpk gmp autoconf automake libtool
    glpk_prefix="$(brew --prefix glpk)"
    gmp_prefix="$(brew --prefix gmp)"
    export LIBTOOLIZE=glibtoolize
else
    glpk_prefix=/usr
    gmp_prefix=/usr
fi
cd vendor/4ti2
autoreconf -fi
./configure --prefix="$prefix" --with-glpk="$glpk_prefix" --with-gmp="$gmp_prefix"
make -j4
make check
make install-exec
