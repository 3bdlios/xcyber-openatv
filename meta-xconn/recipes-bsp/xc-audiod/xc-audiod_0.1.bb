SUMMARY = "XC standard DVB audio system backend"
PR = "r15"
LICENSE = "GPL-2.0-or-later"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-2.0-or-later;md5=fed54355545ffd980b814dab4a3b312c"
SRC_URI = "file://xc-audiod.c file://sync_control.h file://xc-audiod.init"
inherit update-rc.d
INITSCRIPT_NAME = "xc-audiod"
INITSCRIPT_PARAMS = "start 21 S ."
S = "${UNPACKDIR}"
DEPENDS = "ffmpeg alsa-lib"
do_compile() {
 ${CC} ${CFLAGS} ${CPPFLAGS} ${S}/xc-audiod.c -o xc-audiod ${LDFLAGS} -lavcodec -lavutil -lswresample -lasound -lm
}
do_install() {
 install -d ${D}${sbindir}
 install -m 0755 xc-audiod ${D}${sbindir}/xc-audiod
 install -d ${D}${sysconfdir}/init.d
 install -m 0755 ${S}/xc-audiod.init ${D}${sysconfdir}/init.d/xc-audiod
}
