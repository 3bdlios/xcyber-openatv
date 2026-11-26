SUMMARY = "XC subtitle overlay visibility integration"
LICENSE = "CLOSED"
SRC_URI = "file://plugin.py"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core"
do_install() {
    install -d ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCSubtitleOverlayCompat
    touch ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCSubtitleOverlayCompat/__init__.py
    install -m 0644 ${S}/plugin.py ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCSubtitleOverlayCompat/
}
FILES:${PN} += "${libdir}/enigma2/python/Plugins/SystemPlugins/XCSubtitleOverlayCompat"
