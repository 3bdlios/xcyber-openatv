SUMMARY = "XCONN RTL8822CS WiFi startup"
LICENSE = "CLOSED"
SRC_URI = "file://xc-wifi file://rtw_core.ko file://rtw_sdio.ko file://rtw_8822c.ko file://rtw_8822cs.ko"
S = "${UNPACKDIR}"
inherit update-rc.d
RDEPENDS:${PN} += "iw python3-wifi"
INITSCRIPT_NAME = "xc-wifi"
INITSCRIPT_PARAMS = "start 28 S ."
do_install() {
    install -d ${D}${sysconfdir}/init.d ${D}${nonarch_base_libdir}/modules/5.15.196/extra
    install -m 0755 ${S}/xc-wifi ${D}${sysconfdir}/init.d/xc-wifi
    install -m 0644 ${S}/*.ko ${D}${nonarch_base_libdir}/modules/5.15.196/extra/
}
FILES:${PN} += "${nonarch_base_libdir}/modules"
INSANE_SKIP:${PN} += "already-stripped arch"
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
