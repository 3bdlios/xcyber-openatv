SUMMARY = "XC video enhancement: brightness, contrast, saturation and hue on the Amlogic picture engine"
PR = "r12"
LICENSE = "CLOSED"
SRC_URI = "file://XCVideoEnhancement/__init__.py file://XCVideoEnhancement/plugin.py file://XCVideoEnhancement/setup.xml"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core xc-video-setup xc-video-route (>= 0.1-r5)"
PLUGINDIR = "${libdir}/enigma2/python/Plugins/SystemPlugins/XCVideoEnhancement"
do_install() {
    install -d ${D}${PLUGINDIR}
    install -m 0644 ${S}/XCVideoEnhancement/__init__.py ${S}/XCVideoEnhancement/plugin.py ${S}/XCVideoEnhancement/setup.xml ${D}${PLUGINDIR}/
}
FILES:${PN} += "${PLUGINDIR}"
