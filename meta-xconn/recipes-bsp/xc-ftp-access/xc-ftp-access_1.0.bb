SUMMARY = "Start vsftpd at boot and allow passwordless root FTP like telnet/ssh on XC"
LICENSE = "CLOSED"
SRC_URI = "file://xc-ftp-access"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "vsftpd"
do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${S}/xc-ftp-access ${D}${sbindir}/xc-ftp-access
}
pkg_postinst_ontarget:${PN}() {
    ${sbindir}/xc-ftp-access
}
