SUMMARY = "Close native Avahi before reactor shutdown"
LICENSE = "CLOSED"
SRC_URI = "file://plugin.py"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core python3-ctypes"
do_install() {
    install -d ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCAvahiShutdownEarly
    touch ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCAvahiShutdownEarly/__init__.py
    install -m 0644 ${S}/plugin.py ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCAvahiShutdownEarly/
}
FILES:${PN} += "${libdir}/enigma2/python/Plugins/SystemPlugins/XCAvahiShutdownEarly"
