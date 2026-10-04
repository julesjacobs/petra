#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
commit=c8193465bed56654546968bce3a956f0c25c5bee
if [ ! -d vendor/verifypn/.git ]; then
    git clone https://github.com/TAPAAL/verifypn.git vendor/verifypn
    git -C vendor/verifypn checkout --detach "$commit"
fi
test "$(git -C vendor/verifypn rev-parse HEAD)" = "$commit"
test -z "$(git -C vendor/verifypn status --porcelain --untracked-files=no)"
if [ "$(uname -s)" = Darwin ]; then
    PATH="$(brew --prefix flex)/bin:$(brew --prefix bison)/bin:$(brew --prefix gcc)/bin:$PATH"
    export PATH
fi
export GCC_VERSION=16
cd vendor/verifypn
cmake --preset release -DVERIFYPN_OSX_DEPLOYMENT_TARGET=13.0
cmake --build --preset release-deps
cmake --build --preset release
case "$(uname -s)" in
    Darwin) executable=verifypn-osx64 ;;
    Linux) executable=verifypn-linux64 ;;
    *) echo 'Unsupported VerifyPN build platform' >&2; exit 1 ;;
esac
ln -sf "$executable" build-release/verifypn/bin/verifypn
build-release/verifypn/bin/verifypn --version
