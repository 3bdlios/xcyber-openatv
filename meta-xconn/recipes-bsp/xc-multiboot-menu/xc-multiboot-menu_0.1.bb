SUMMARY = "XC installed images, recovery and Android power menu"
LICENSE = "CLOSED"
SRC_URI = "file://XCSlots file://XCAndroidRestart file://helpers"
S = "${UNPACKDIR}"
# subprocess is part of python3-core in Python 3.14
RDEPENDS:${PN} = "python3-core python3-json python3-ctypes"
do_install() {
    install -d ${D}${libdir}/enigma2/python/Plugins/SystemPlugins ${D}${libdir}/xcenigma
    cp -r ${S}/XCSlots ${S}/XCAndroidRestart ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/
    install -m 0644 ${S}/helpers/*.py ${D}${libdir}/xcenigma/
}
FILES:${PN} += "${libdir}/enigma2/python/Plugins/SystemPlugins/XCSlots ${libdir}/enigma2/python/Plugins/SystemPlugins/XCAndroidRestart ${libdir}/xcenigma"
