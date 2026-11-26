SUMMARY = "XC mounted timeshift storage recovery"
LICENSE = "CLOSED"
SRC_URI = "file://plugin.py"
S = "${UNPACKDIR}"
do_install() {
    install -d ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCTimeshiftStorage
    install -m 0644 ${S}/plugin.py ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCTimeshiftStorage/
    touch ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/XCTimeshiftStorage/__init__.py
}
FILES:${PN} += "${libdir}/enigma2"
