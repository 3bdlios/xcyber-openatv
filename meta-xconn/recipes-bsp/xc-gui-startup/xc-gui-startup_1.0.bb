SUMMARY = "Minimal XC hardware and framebuffer startup for OpenATV GUI"
PR = "r2"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=e6a75371ba4d16749254a51215d13f97"
SRC_URI = "file://COPYING file://xc-gui-startup file://xc-nec.toml"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-gui-startup"
INITSCRIPT_PARAMS = "start 20 S ."
RDEPENDS:${PN} = "xc-hardware ir-keytable xc-image-name xc-password-pam-fix"
do_install() {
 install -d ${D}${sysconfdir}/init.d
 install -m 0755 ${UNPACKDIR}/xc-gui-startup ${D}${sysconfdir}/init.d/xc-gui-startup
 install -m 0644 ${UNPACKDIR}/xc-nec.toml ${D}${sysconfdir}/xc-nec.toml
}
