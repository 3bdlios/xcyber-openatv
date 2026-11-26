SUMMARY = "XC IPAudioPlus delay/sync panel and native XC PCM reopen helper"
LICENSE = "CLOSED"
SRC_URI = "file://XCIPADelayControls/__init__.py file://XCIPADelayControls/plugin.py file://xc-audio-reopen file://XCIPADelayControls/keymap.xml"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core xc-audiod"
PLUGINDIR = "${libdir}/enigma2/python/Plugins/SystemPlugins/XCIPADelayControls"
do_install() {
    install -d ${D}${PLUGINDIR} ${D}${sbindir}
    install -m 0644 ${S}/XCIPADelayControls/*.py ${D}${PLUGINDIR}/
    if ls ${S}/XCIPADelayControls/*.xml >/dev/null 2>&1; then install -m 0644 ${S}/XCIPADelayControls/*.xml ${D}${PLUGINDIR}/; fi
    install -m 0755 ${S}/xc-audio-reopen ${D}${sbindir}/xc-audio-reopen
}
FILES:${PN} += "${PLUGINDIR}"
