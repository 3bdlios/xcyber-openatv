# XC uses the verified prebuilt kernel and module bundle. Do not request
# optional module subpackages generated only by the upstream kernel recipe.
RRECOMMENDS:${PN}:remove = "kernel-module-xfs kernel-module-exportfs kernel-module-fat kernel-module-msdos kernel-module-vfat kernel-module-nls-cp437 kernel-module-nls-iso8859-1 kernel-module-nls-iso8859-15"
