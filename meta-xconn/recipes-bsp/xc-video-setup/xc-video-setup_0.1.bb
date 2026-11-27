SUMMARY = "XC video output: resolution from the TV's DRM modes (applied at boot) and HDR output policy"
PR = "r3"
LICENSE = "CLOSED"
SRC_URI = "file://XCVideo.py file://XCVideoSetup/__init__.py file://XCVideoSetup/plugin.py"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core"
PLUGINDIR = "${libdir}/enigma2/python/Plugins/SystemPlugins/XCVideoSetup"
do_install() {
    install -d ${D}${libdir}/enigma2/python/Components ${D}${PLUGINDIR}
    install -m 0644 ${S}/XCVideo.py ${D}${libdir}/enigma2/python/Components/XCVideo.py
    install -m 0644 ${S}/XCVideoSetup/__init__.py ${S}/XCVideoSetup/plugin.py ${D}${PLUGINDIR}/
}
FILES:${PN} += "${libdir}/enigma2/python/Components/XCVideo.py ${PLUGINDIR}"
