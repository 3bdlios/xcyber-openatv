# XC ships its matching hardware bundle; do not build foreign USB adapter modules.
RDEPENDS:${PN}:remove = "network-usb-drivers-meta packagegroup-oea-wifi"
