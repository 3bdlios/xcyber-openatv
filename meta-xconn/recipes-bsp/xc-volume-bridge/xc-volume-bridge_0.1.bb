SUMMARY = "XC: mirror Enigma2 volume/mute to the ALSA softvol used by IPTV/GStreamer and other ALSA clients"
PR = "r1"
LICENSE = "CLOSED"
SRC_URI = "file://xc-volume-bridge file://xc-volume-bridge.init"
S = "${UNPACKDIR}"
inherit update-rc.d
INITSCRIPT_NAME = "xc-volume-bridge"
INITSCRIPT_PARAMS = "start 40 S ."
RDEPENDS:${PN} = "python3-core alsa-utils-amixer alsa-state"
do_install() {
    install -d ${D}${sbindir} ${D}${sysconfdir}/init.d
    install -m 0755 ${S}/xc-volume-bridge ${D}${sbindir}/xc-volume-bridge
    install -m 0755 ${S}/xc-volume-bridge.init ${D}${sysconfdir}/init.d/xc-volume-bridge
}
