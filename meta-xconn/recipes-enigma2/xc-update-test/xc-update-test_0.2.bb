SUMMARY = "Harmless GitHub feed delivery test"
LICENSE = "CLOSED"
SRC_URI = "file://plugin.py"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "enigma2 python3-core"
PACKAGES = "${PN}"
PKG:${PN} = "enigma2-plugin-extensions-xc-update-test"
do_install() {
    install -d ${D}${libdir}/enigma2/python/Plugins/Extensions/XCUpdateTest ${D}${datadir}/xc-update-test
    touch ${D}${libdir}/enigma2/python/Plugins/Extensions/XCUpdateTest/__init__.py
    install -m 0644 ${S}/plugin.py ${D}${libdir}/enigma2/python/Plugins/Extensions/XCUpdateTest/
    echo "0.2" > ${D}${datadir}/xc-update-test/version
}
FILES:${PN} = "${libdir}/enigma2/python/Plugins/Extensions/XCUpdateTest ${datadir}/xc-update-test"
