SUMMARY = "Repair malformed Samba PAM password stack on XC OpenATV"
LICENSE = "CLOSED"
SRC_URI = "file://fix-password-pam.sh"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "libpam-runtime"
do_install() {
    install -d ${D}${libdir}/xcenigma
    install -m 0755 ${S}/fix-password-pam.sh ${D}${libdir}/xcenigma/
}
pkg_postinst:${PN}() {
    sh "$D${libdir}/xcenigma/fix-password-pam.sh" "$D"
}
FILES:${PN} = "${libdir}/xcenigma/fix-password-pam.sh"
