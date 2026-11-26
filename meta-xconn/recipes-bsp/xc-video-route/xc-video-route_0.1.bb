SUMMARY = "XC deinterlaced video route and HDMI/OSD binding"
LICENSE = "CLOSED"
PR = "r5"
SRC_URI = "file://xc-video-route file://xc-video-route.init file://xc-display-fix"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-video-route"
INITSCRIPT_PARAMS = "start 27 S ."
RDEPENDS:${PN} = "python3-core python3-ctypes python3-fcntl"
do_install() {
    install -d ${D}${sbindir} ${D}${sysconfdir}/init.d
    install -m 0755 ${S}/xc-video-route ${D}${sbindir}/xc-video-route
    install -m 0755 ${S}/xc-display-fix ${D}${sbindir}/xc-display-fix
    install -m 0755 ${S}/xc-video-route.init ${D}${sysconfdir}/init.d/xc-video-route
}
