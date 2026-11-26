# ARM64 naming aliases used by third-party IPK producers. Prefer the native tune.
do_install:append() {
 conf=${D}${sysconfdir}/opkg/arch.conf
 grep -q '^arch aarch64 ' "$conf" || printf 'arch aarch64 15\n' >> "$conf"
 grep -q '^arch arm64 ' "$conf" || printf 'arch arm64 14\n' >> "$conf"
}
