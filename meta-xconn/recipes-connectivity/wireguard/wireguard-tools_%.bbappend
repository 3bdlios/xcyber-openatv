# The stock tools recommend an out-of-tree module for every machine.
# XC uses its fixed 5.15.196 bundle, which contains no WireGuard module.
# Keep userspace tools available without building an incompatible module.
RRECOMMENDS:${PN}:remove = "kernel-module-wireguard wireguard-module"
