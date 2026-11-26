SUMMARY = "XC deinterlaced video route and HDMI/OSD binding"
LICENSE = "CLOSED"
PR = "r6"
SRC_URI = "file://xc-video-route file://xc-video-route.init file://xc-display-fix file://xc-hdr-auto"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-video-route"
INITSCRIPT_PARAMS = "start 27 S ."
RDEPENDS:${PN} = "python3-core python3-ctypes python3-fcntl"
do_install() {
    install -d ${D}${sbindir} ${D}${sysconfdir}/init.d
    install -m 0755 ${S}/xc-video-route ${D}${sbindir}/xc-video-route
    install -m 0755 ${S}/xc-display-fix ${D}${sbindir}/xc-display-fix
    install -m 0755 ${S}/xc-hdr-auto ${D}${sbindir}/xc-hdr-auto
    install -m 0755 ${S}/xc-video-route.init ${D}${sysconfdir}/init.d/xc-video-route
}

pkg_postinst:${PN}:append() {

# Start only the HDR watcher during a live upgrade; do not restart playback.
if [ -z "${D:-}" ]; then
    start-stop-daemon -K -p /run/xc-hdr-auto.pid 2>/dev/null || true
    rm -f /run/xc-hdr-auto.pid
    start-stop-daemon -S -b -m -p /run/xc-hdr-auto.pid -x /usr/sbin/xc-hdr-auto
fi
}
