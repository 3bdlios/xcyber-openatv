SUMMARY = "XC HDMI routing for physical SPDIF PCM clients"
LICENSE = "CLOSED"
SRC_URI = "file://xc-hdmi-route file://xc-hdmi-route.init"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-hdmi-route"
INITSCRIPT_PARAMS = "start 25 S . stop 15 0 6 ."
RDEPENDS:${PN} = "python3-core python3-ctypes python3-fcntl alsa-lib"
do_install() {
    install -d ${D}${sbindir} ${D}${sysconfdir}/init.d
    install -m 0755 ${S}/xc-hdmi-route ${D}${sbindir}/xc-hdmi-route
    install -m 0755 ${S}/xc-hdmi-route.init ${D}${sysconfdir}/init.d/xc-hdmi-route
}
