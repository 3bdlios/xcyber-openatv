SUMMARY = "Use the XC STORAGE partition as /media/hdd (recordings, timeshift, HDD in Enigma2)"
LICENSE = "CLOSED"
SRC_URI = "file://xc-storage-hdd"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-storage-hdd"
INITSCRIPT_PARAMS = "start 04 S ."
do_install() {
    install -d ${D}${sysconfdir}/init.d
    install -m 0755 ${S}/xc-storage-hdd ${D}${sysconfdir}/init.d/xc-storage-hdd
}
