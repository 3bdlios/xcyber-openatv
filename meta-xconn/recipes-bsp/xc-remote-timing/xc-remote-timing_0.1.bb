SUMMARY = "XC IR remote held-key timing"
LICENSE = "CLOSED"
PR = "r1"
SRC_URI = "file://xc-remote-timing file://xc-remote-timing.init"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-remote-timing"
INITSCRIPT_PARAMS = "start 26 S ."
RDEPENDS:${PN} = "python3-core python3-fcntl xc-addremote-repeat"
do_install() {
    install -d ${D}${sbindir} ${D}${sysconfdir}/init.d
    install -m 0755 ${S}/xc-remote-timing ${D}${sbindir}/xc-remote-timing
    install -m 0755 ${S}/xc-remote-timing.init ${D}${sysconfdir}/init.d/xc-remote-timing
}
