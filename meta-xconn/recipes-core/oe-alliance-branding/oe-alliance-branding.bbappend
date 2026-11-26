# XC has no upstream device photograph; it is optional presentation data.
python () {
    body = d.getVar("do_install", False)
    old = 'else\n        install -m 0644 ${S}/BoxBranding/boxes/${MACHINEBUILD}.png'
    new = 'elif [ -f ${S}/BoxBranding/boxes/${MACHINEBUILD}.png ]; then\n        install -m 0644 ${S}/BoxBranding/boxes/${MACHINEBUILD}.png'
    if old not in body:
        bb.fatal("XC optional device image fix no longer matches upstream")
    d.setVar("do_install", body.replace(old, new, 1))
}

# Keep package revision stable across midnight and cached packaging metadata.
PR = "r20261118-xconn"

# XCONN X-CYBER remote: RcModel (installed from this branding module) maps xconn to
# rc_models/xconn (picture and key positions from oe-alliance-remote).
do_configure:append() {
    if ! grep -q '"xconn": "xconn"' ${S}/BoxBranding/RcModel.py; then
        sed -i 's/^\(\t\t\t"xcombo": "evo3",\)$/\1\n\t\t\t"xconn": "xconn",/' ${S}/BoxBranding/RcModel.py
        grep -q '"xconn": "xconn"' ${S}/BoxBranding/RcModel.py || bbfatal "XC RcModel mapping did not apply"
    fi
}

