SUMMARY = "Normalize the current OpenATV slot display name"
LICENSE = "CLOSED"
SRC_URI = "file://update-image-name.py"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "python3-core python3-json"
do_install() {
    install -d ${D}${libdir}/xcenigma
    install -m 0644 ${S}/update-image-name.py ${D}${libdir}/xcenigma/
}
pkg_postinst:${PN}() {
    [ -n "$D" ] || python3 ${libdir}/xcenigma/update-image-name.py
}
FILES:${PN} = "${libdir}/xcenigma/update-image-name.py"
