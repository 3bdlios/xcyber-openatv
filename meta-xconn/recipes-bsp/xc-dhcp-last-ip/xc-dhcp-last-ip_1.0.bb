SUMMARY = "Ask the DHCP server for the address the box had last time, so the IP survives expired leases"
LICENSE = "CLOSED"
SRC_URI = "file://udhcpc file://60xc-last-ip"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "busybox-udhcpc"
# /usr/local/sbin comes first in PATH of /etc/init.d/networking, so ifup runs this wrapper.
do_install() {
    install -d ${D}${prefix}/local/sbin ${D}${sysconfdir}/udhcpc.d
    install -m 0755 ${S}/udhcpc ${D}${prefix}/local/sbin/udhcpc
    install -m 0755 ${S}/60xc-last-ip ${D}${sysconfdir}/udhcpc.d/60xc-last-ip
}
FILES:${PN} = "${prefix}/local/sbin/udhcpc ${sysconfdir}/udhcpc.d/60xc-last-ip"
