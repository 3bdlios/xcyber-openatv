# Repair the upstream echo -e PAM line after samba-common's postinstall.
PR:append:xconn = ".xc1"
RDEPENDS:${PN}-common:append:xconn = " xc-password-pam-fix"
pkg_postinst:${BPN}-common:append:xconn() {
    sh "$D${libdir}/xcenigma/fix-password-pam.sh" "$D"
}
