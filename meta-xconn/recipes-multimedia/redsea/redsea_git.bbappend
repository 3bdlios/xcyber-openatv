# The only LFS objects are two FLAC fixtures under test/resources.
# The installed decoder uses source files only; upstream build_tests is off.
SRC_URI = "git://github.com/windytan/redsea.git;protocol=https;branch=master;lfs=0 file://remove-hardcoded-build-path.patch"
