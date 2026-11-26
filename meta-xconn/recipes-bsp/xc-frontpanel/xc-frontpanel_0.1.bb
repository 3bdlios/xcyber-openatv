SUMMARY = "XC front panel display: boot counter, channel, menus and clock on the 4-digit 7-segment panel"
LICENSE = "CLOSED"
SRC_URI = "file://xc-fpd file://xc-frontpanel.init file://xc-frontpanel.conf file://XCFrontPanel/__init__.py file://XCFrontPanel/plugin.py"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-frontpanel"
INITSCRIPT_PARAMS = "start 04 S . stop 20 0 6 ."
RDEPENDS:${PN} = "python3-core python3-fcntl"
CONFFILES:${PN} = "${sysconfdir}/xc-frontpanel.conf"
PLUGINDIR = "${libdir}/enigma2/python/Plugins/SystemPlugins/XCFrontPanel"
do_install() {
    install -d ${D}${sbindir} ${D}${sysconfdir}/init.d ${D}${PLUGINDIR}
    install -m 0755 ${S}/xc-fpd ${D}${sbindir}/xc-fpd
    install -m 0755 ${S}/xc-frontpanel.init ${D}${sysconfdir}/init.d/xc-frontpanel
    install -m 0644 ${S}/xc-frontpanel.conf ${D}${sysconfdir}/xc-frontpanel.conf
    install -m 0644 ${S}/XCFrontPanel/__init__.py ${S}/XCFrontPanel/plugin.py ${D}${PLUGINDIR}/
}
FILES:${PN} += "${PLUGINDIR}"
