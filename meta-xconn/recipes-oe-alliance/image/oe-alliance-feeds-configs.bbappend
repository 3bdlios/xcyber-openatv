# Independent X-CYBER package feed. No private/static distro feeds.
PR:append:xconn = ".xc1"
FEEDS:xconn = "all cortexa55 xconn"
DISTRO_FEED_URI:xconn = "https://raw.githubusercontent.com/3bdlios/xcyber-openatv/main/feeds/openatv-8.0.1/xconn"

# Match the configuration installed on existing receivers by install-feed.sh.
do_compile:append:xconn() {
    rm -f ${S}${sysconfdir}/opkg/*-feed.conf
    for feed in ${FEEDS}; do
        echo "src/gz xc-openatv-${feed} ${DISTRO_FEED_URI}/${feed}"
    done > ${S}${sysconfdir}/opkg/xcyber-openatv-feed.conf
    echo "src/gz xc-openatv-debug https://github.com/3bdlios/xcyber-openatv/releases/download/feed-debug-8.0.1-20261125" >> ${S}${sysconfdir}/opkg/xcyber-openatv-feed.conf
}
CONFFILES:${PN}:xconn = "${sysconfdir}/opkg/xcyber-openatv-feed.conf"
