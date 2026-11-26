# Use cmp for content equality without invoking BusyBox diff during DHCP updates.
PR:append = ".xc2"

python xcyber_fix_resolver_compare() {
    from pathlib import Path
    script = Path(d.expand("${D}${sbindir}/odhcp6c-update"))
    text = script.read_text()
    variants = {
        'if diff "$resolvconf" "$myresolvconf" >/dev/null; then':
            'if cmp -s "$resolvconf" "$myresolvconf"; then',
        'if diff -q "$RESOLV_CONF" "$etmp" >/dev/null 2>&1; then':
            'if cmp -s "$RESOLV_CONF" "$etmp"; then',
    }
    matches = sum(text.count(old) for old in variants)
    if matches != 1:
        bb.fatal("XC odhcp6c: expected exactly one supported resolver comparison, found %d" % matches)
    for old, new in variants.items():
        text = text.replace(old, new)
    script.write_text(text)
}

do_install[postfuncs] += "xcyber_fix_resolver_compare"
