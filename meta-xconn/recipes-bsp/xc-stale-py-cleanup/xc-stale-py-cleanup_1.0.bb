SUMMARY = "Move aside leftover Enigma2 .py files that shadow packaged .pyc updates"
LICENSE = "CLOSED"
SRC_URI = "file://xc-stale-py-cleanup"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core"
do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${S}/xc-stale-py-cleanup ${D}${sbindir}/xc-stale-py-cleanup
}
pkg_postinst_ontarget:${PN}() {
    ${sbindir}/xc-stale-py-cleanup || true
}
