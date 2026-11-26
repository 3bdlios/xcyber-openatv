SUMMARY = "XC Amlogic encoded IPTV GStreamer video output"
LICENSE = "CLOSED"
DEPENDS = "gstreamer1.0 gstreamer1.0-plugins-base"
SRC_URI = "file://gstxcamlvideo.c"
S = "${UNPACKDIR}"
inherit pkgconfig
do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} -fPIC -shared ${S}/gstxcamlvideo.c ${LDFLAGS} $(pkg-config --cflags --libs gstreamer-base-1.0 gstreamer-video-1.0) -o libgstxcamlvideo.so
}
do_install() {
    install -d ${D}${libdir}/gstreamer-1.0
    install -m 0755 ${B}/libgstxcamlvideo.so ${D}${libdir}/gstreamer-1.0/
}
FILES:${PN} += "${libdir}/gstreamer-1.0"
