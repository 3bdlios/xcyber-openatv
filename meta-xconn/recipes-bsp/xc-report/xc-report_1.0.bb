SUMMARY = "XC support report: diagnostic report (with screenshot) sent to the support repository"
PR = "r6"
LICENSE = "CLOSED"
SRC_URI = "file://xc-report file://XCReport/__init__.py file://XCReport/plugin.py file://XCReport/plugin.png file://XCReport/xcreport.png file://report.conf"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core python3-json python3-netclient python3-compression python3-threading enigma2-plugin-extensions-openwebif"
PLUGINDIR = "${libdir}/enigma2/python/Plugins/SystemPlugins/XCReport"
do_install() {
    install -d ${D}${bindir} ${D}${PLUGINDIR} ${D}${sysconfdir}/xc
    install -m 0755 ${S}/xc-report ${D}${bindir}/xc-report
    install -m 0644 ${S}/XCReport/__init__.py ${S}/XCReport/plugin.py ${S}/XCReport/plugin.png ${S}/XCReport/xcreport.png ${D}${PLUGINDIR}/
    # holds the upload token: readable by root only
    install -m 0600 ${S}/report.conf ${D}${sysconfdir}/xc/report.conf
}
CONFFILES:${PN} = "${sysconfdir}/xc/report.conf"
FILES:${PN} += "${PLUGINDIR}"
