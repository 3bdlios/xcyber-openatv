FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += " file://xc-wifi-scan.py"
RDEPENDS:${PN} += "iw"
do_install:append() {
    install -m 0644 ${UNPACKDIR}/xc-wifi-scan.py ${D}${PYTHON_SITEPACKAGES_DIR}/wifi/scan.py
}
