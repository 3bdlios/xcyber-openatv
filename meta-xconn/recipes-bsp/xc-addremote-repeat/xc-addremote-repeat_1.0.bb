SUMMARY = "Faster held-key repeat for the Add Remote plugin on XC"
LICENSE = "CLOSED"
SRC_URI = "file://xc-addremote-repeat file://xc-addremote-repeat.init file://keyflow.py"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-addremote-repeat"
INITSCRIPT_PARAMS = "start 30 S ."
RDEPENDS:${PN} = "python3-core"
do_install() {
    install -d ${D}${sbindir} ${D}${sysconfdir}/init.d ${D}${datadir}/xc-addremote-repeat
    install -m 0755 ${S}/xc-addremote-repeat ${D}${sbindir}/xc-addremote-repeat
    install -m 0755 ${S}/xc-addremote-repeat.init ${D}${sysconfdir}/init.d/xc-addremote-repeat
    install -m 0644 ${S}/keyflow.py ${D}${datadir}/xc-addremote-repeat/keyflow.py
}
pkg_postinst_ontarget:${PN}() {
    ${sbindir}/xc-addremote-repeat apply || true
}
pkg_prerm:${PN}() {
    if [ -z "$D" ]; then
        ${sbindir}/xc-addremote-repeat restore || true
    fi
}
