# Keep the official metadata task compatible with Debian /bin/sh (dash), and
# give the XC machine a real drivers date (the verified module bundle in xc-hardware).
python () {
    body = d.getVar("do_install", False)
    old = 'cleaned_variable="${variable//.%/}"'
    new = "cleaned_variable=\"$(printf '%s' \"$variable\" | sed 's/\\.%//g')\""
    if old not in body:
        bb.fatal("XC enigma-info portability fix no longer matches upstream")
    body = body.replace(old, new, 1)
    if d.getVar("XC_DRIVERSDATE"):
        old_date = "DRIVERSDATE='N/A'"
        if old_date not in body:
            bb.fatal("XC enigma-info drivers date hook no longer matches upstream")
        body = body.replace(old_date, "DRIVERSDATE='${XC_DRIVERSDATE}'", 1)
    d.setVar("do_install", body)
}
