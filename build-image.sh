#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$ROOT/build-environment/bitbake/bin:$ROOT/build-environment/openembedded-core/scripts:$PATH"
export MACHINE=xconn MACHINEBUILD=xconn DISTRO=openatv
export BB_ENV_PASSTHROUGH_ADDITIONS="MACHINE MACHINEBUILD DISTRO"
cd "$ROOT/build-environment/builds/openatv/release/xconn"
exec bitbake "$@"
