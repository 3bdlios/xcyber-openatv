FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI:append = " file://0001-libdeflate-preserve-cortexa55-target.patch"
PR:append = ".xc1"
