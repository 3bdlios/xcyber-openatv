SUMMARY = "XC OpenWebif screenshot: Amlogic video capture (amvideocap0) plus OSD framebuffer"
LICENSE = "CLOSED"
PR = "r1"
SRC_URI = "file://XCScreenshot/__init__.py file://XCScreenshot/plugin.py file://XCScreenshot/capture.py"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core python3-pillow python3-fcntl python3-ctypes enigma2-plugin-extensions-openwebif"
PLUGINDIR = "${libdir}/enigma2/python/Plugins/SystemPlugins/XCScreenshot"
do_install() {
    install -d ${D}${PLUGINDIR}
    install -m 0644 ${S}/XCScreenshot/__init__.py ${S}/XCScreenshot/plugin.py ${D}${PLUGINDIR}/
    install -m 0755 ${S}/XCScreenshot/capture.py ${D}${PLUGINDIR}/capture.py
}
FILES:${PN} += "${PLUGINDIR}"
