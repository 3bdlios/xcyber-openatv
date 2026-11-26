SUMMARY = "XC standard softcam integration for OpenBH"
LICENSE = "CLOSED"
SRC_URI = "file://XCCamIntegration.py file://xc-cam-integrate"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core"
do_install() {
    install -d ${D}${libdir}/enigma2/python/Components ${D}${sbindir}
    install -m 0644 ${S}/XCCamIntegration.py ${D}${libdir}/enigma2/python/Components/
    install -m 0755 ${S}/xc-cam-integrate ${D}${sbindir}/
}
FILES:${PN} += "${libdir}/enigma2/python/Components/XCCamIntegration.py"
