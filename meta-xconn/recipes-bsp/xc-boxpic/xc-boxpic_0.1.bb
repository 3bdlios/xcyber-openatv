SUMMARY = "XCONN X-CYBER receiver picture for OpenWebif Box Info (/usr/share/enigma2/hardware/<machinebuild>_front.png)"
LICENSE = "CLOSED"
SRC_URI = "file://xconn_front.png"
S = "${UNPACKDIR}"
PACKAGE_ARCH = "${MACHINE_ARCH}"
do_install() {
    install -d ${D}${datadir}/enigma2/hardware
    install -m 0644 ${S}/xconn_front.png ${D}${datadir}/enigma2/hardware/xconn_front.png
}
FILES:${PN} = "${datadir}/enigma2/hardware/xconn_front.png"
