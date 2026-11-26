SUMMARY = "XC picture in picture: xc-pipd plays Enigma2's video1 on a second decoder"
LICENSE = "CLOSED"
PR = "r1"
SRC_URI = "file://xc-pipd file://xc-pipd.init"
S = "${UNPACKDIR}"
# xc_pipsync.ko (pacing) and the video1 demux driver come with xc-hardware; the PiP close
# path also needs the XC kernel with the videopip disable fix (xc-boot-files).
RDEPENDS:${PN} = "python3-core python3-fcntl python3-threading"
inherit update-rc.d
INITSCRIPT_NAME = "xc-pipd"
INITSCRIPT_PARAMS = "start 22 S ."
do_install() {
    install -d ${D}${bindir} ${D}${sysconfdir}/init.d
    install -m 0755 ${S}/xc-pipd ${D}${bindir}/xc-pipd
    install -m 0755 ${S}/xc-pipd.init ${D}${sysconfdir}/init.d/xc-pipd
}
