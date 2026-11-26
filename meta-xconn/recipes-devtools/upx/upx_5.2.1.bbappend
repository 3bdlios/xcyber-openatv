# UPX invokes a nested CMake build, independent of make -j.
EXTRA_OEMAKE:append = " UPX_CMAKE_BUILD_FLAGS='--parallel 1'"
export CMAKE_BUILD_PARALLEL_LEVEL = "1"
