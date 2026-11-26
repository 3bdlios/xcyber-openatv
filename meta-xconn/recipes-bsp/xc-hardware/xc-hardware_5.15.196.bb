SUMMARY = "Verified XC kernel modules and firmware for the shared 5.15.196 boot kernel"
PR = "r1"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=e6a75371ba4d16749254a51215d13f97"
SRC_URI = "file://hardware.tar.gz;unpack=0 file://COPYING"
S = "${UNPACKDIR}"
PROVIDES += "virtual/kernel"
PACKAGE_ARCH = "${MACHINE_ARCH}"
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
RPROVIDES:${PN} += "kernel-base kernel-image kernel-modules"
FILES:${PN} = "/lib/modules /lib/firmware"
do_configure[noexec] = "1"
do_compile[noexec] = "1"
do_install() {
    install -d ${D}
    tar -xzf ${UNPACKDIR}/hardware.tar.gz -C ${D}
}

RPROVIDES:${PN} += "kernel-module-aml-hardware-dmx kernel-module-amlogic-dvb-demux kernel-module-amvdec-h265 kernel-module-amvdec-mh264 kernel-module-amvdec-mmpeg12 kernel-module-cxd2878 kernel-module-decoder-common kernel-module-firmware kernel-module-gtcombo-dvb-wrapper kernel-module-ir-nec-decoder kernel-module-m88rs6000t kernel-module-m88rs6060 kernel-module-media-clock kernel-module-meson-ir kernel-module-pts-server kernel-module-stream-input"

# TUN is built into the shared kernel: CONFIG_TUN=y; verified /sys/class/misc/tun.
RPROVIDES:${PN} += "kernel-module-tun"

# Match the normal OE kernel module namespace. Optional recommendations for
# modules absent from this verified bundle may be skipped by the package manager;
# hard dependencies still must resolve to a real installed package.
PACKAGES_DYNAMIC += "^kernel-module-.*"

inherit deploy
SRC_URI:append = " file://kernel.img;unpack=0"
do_deploy() {
 install -d ${DEPLOYDIR}
 install -m 0644 ${UNPACKDIR}/kernel.img ${DEPLOYDIR}/Image
 install -m 0644 ${UNPACKDIR}/kernel.img ${DEPLOYDIR}/kernel.img
}
addtask deploy after do_install before do_build

# The official wireless-regdb-static package owns the signed regulatory database.
# Keep hardware firmware, but avoid packaging a second copy of these files.
do_install:append() {
 rm -f ${D}/lib/firmware/regulatory.db ${D}/lib/firmware/regulatory.db.p7s
}
