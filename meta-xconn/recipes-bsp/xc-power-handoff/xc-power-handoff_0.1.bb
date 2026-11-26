SUMMARY = "XC deep standby: blank front panel and arm BL30 IR wake (vendor meson-remote) at poweroff"
LICENSE = "CLOSED"
SRC_URI = "file://xc-power-handoff.py file://xc-power-handoff.init file://meson-remote.ko file://amlogic-gkitool.ko"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-power-handoff"
INITSCRIPT_PARAMS = "stop 35 0 ."
RDEPENDS:${PN} = "python3-core xc-frontpanel xc-hardware"
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
INSANE_SKIP:${PN} += "arch already-stripped"
do_install() {
    install -d ${D}${sbindir} ${D}${sysconfdir}/init.d ${D}${libdir}/xc/ir-wake
    install -m 0755 ${S}/xc-power-handoff.py ${D}${sbindir}/xc-power-handoff
    install -m 0755 ${S}/xc-power-handoff.init ${D}${sysconfdir}/init.d/xc-power-handoff
    install -m 0644 ${S}/meson-remote.ko ${S}/amlogic-gkitool.ko ${D}${libdir}/xc/ir-wake/
}
FILES:${PN} += "${libdir}/xc/ir-wake"
