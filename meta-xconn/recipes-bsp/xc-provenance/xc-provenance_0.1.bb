SUMMARY = "XC provenance: public key and verifier for the stamped XC kernel modules (xc-provenance verify)"
LICENSE = "CLOSED"
SRC_URI = "file://xc-provenance file://provenance.pub"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "python3-core openssl-bin"
do_install() {
    install -d ${D}${bindir} ${D}${sysconfdir}/xc
    install -m 0755 ${S}/xc-provenance ${D}${bindir}/xc-provenance
    install -m 0644 ${S}/provenance.pub ${D}${sysconfdir}/xc/provenance.pub
}
