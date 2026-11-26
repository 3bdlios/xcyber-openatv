# Samba keeps its private shared libraries in a subdirectory. Allow the
# cross linker to resolve libsmbclient's indirect dependencies there.
LDFLAGS:append = " -Wl,-rpath-link,${STAGING_LIBDIR}/samba"
PR:append = ".xc1"
