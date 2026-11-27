SUMMARY = "Minimal XC hardware and framebuffer startup for OpenATV GUI"
PR = "r4"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=e6a75371ba4d16749254a51215d13f97"
SRC_URI = "file://COPYING file://xc-gui-startup file://xc-nec.toml"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-gui-startup"
INITSCRIPT_PARAMS = "start 20 S ."
RDEPENDS:${PN} = "xc-hardware ir-keytable xc-image-name xc-password-pam-fix xc-power-handoff xc-volume-bridge xc-audiod (>= 0.1-r15) xc-video-enhancement (>= 1.0-r12) xc-video-setup (>= 0.1-r3)"
do_install() {
 install -d ${D}${sysconfdir}/init.d
 install -m 0755 ${UNPACKDIR}/xc-gui-startup ${D}${sysconfdir}/init.d/xc-gui-startup
 install -m 0644 ${UNPACKDIR}/xc-nec.toml ${D}${sysconfdir}/xc-nec.toml
}
