# This image uses the matching XC kernel bundle; foreign USB drivers require
# a different kernel build tree and must not be advertised as XC-compatible.
RDEPENDS:${PN}:remove = "dvb-usb-drivers-meta extrahw-drivers-meta network-usb-drivers-meta enigma2-plugin-drivers-usbserial"
WIREGUARD_MODULE = ""

# dmxcsa locates a per-machine module through a staged kernel source tree.
# XC provides a prebuilt kernel bundle, without that source-tree task.
RDEPENDS:${PN}:remove = "dmxcsa"
