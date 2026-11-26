# Preserve remote resources; the unsupported device photograph is optional.
python () {
    body = d.getVar("do_install", False)
    old = 'else\n        install -m 0644 ${S}/boxes/${MACHINEBUILD}.png'
    new = 'elif [ -f ${S}/boxes/${MACHINEBUILD}.png ]; then\n        install -m 0644 ${S}/boxes/${MACHINEBUILD}.png'
    if old not in body:
        bb.fatal("XC optional remote device image fix no longer matches upstream")
    body = body.replace(old, new, 1)
    body = body.replace('${RCHARDWARE} ==', '\"${RCHARDWARE}\" =')
    d.setVar("do_install", body)
}

# XCONN X-CYBER remote picture and key positions (first-run wizard, help screens),
# installed under the machine's RCNAME so every consumer picks them up.
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI:append = " file://xconn-rc.png file://xconn-rc.xml"
do_install:append() {
    for d in hardware rc; do
        install -m 0644 ${UNPACKDIR}/xconn-rc.png ${D}${datadir}/enigma2/$d/${RCNAME}.png
        install -m 0644 ${UNPACKDIR}/xconn-rc.xml ${D}${datadir}/enigma2/$d/${RCNAME}.xml
    done
}
do_install:append() {
    # Default ("branding") remote source: RcModel maps xconn -> rc_models/xconn.
    install -d ${D}${datadir}/enigma2/rc_models/xconn
    install -m 0644 ${UNPACKDIR}/xconn-rc.png ${D}${datadir}/enigma2/rc_models/xconn/rc.png
    install -m 0644 ${UNPACKDIR}/xconn-rc.xml ${D}${datadir}/enigma2/rc_models/xconn/rcpositions.xml
}
FILES:${PN} += "${datadir}/enigma2/rc_models/xconn"
