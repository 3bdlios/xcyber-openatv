# OpenATV for XCONN X-CYBER

Independent, experimental OpenATV 8.0.1 / OE-Alliance 6.0 adaptation for the XC 5.15.196 kernel. Not an official supported OpenATV machine.

## Package feed

The matching IPK feed is published under `feeds/openatv-8.0.1/xconn`. Use the installer in `scripts` to back up and replace the unavailable default machine feeds. Shared channel-settings, picon and third-party feeds are retained. Do not use OpenBlackHole feeds with this image.

The initial feed mirrors the completed 2026-11-25 OpenATV build. On-device compatibility fixes are in `meta-xconn`; they are not all rebuilt into IPKs yet. This initial publication is for installing compatible dependencies. Do not perform a full system upgrade or reinstall Enigma2 until a tested fix release is published.

## Sources and build

`source-lock.json` pins the upstream environment and layers. `meta-xconn` contains the machine recipes and local patches, including the current wizard, DRM, HDR, hardware-identity and XC recovery-menu adaptations. The prebuilt XC kernel/modules are reused, not rebuilt from kernel source in this project.

Install the pinned official OE-Alliance build environment in `build-environment`, overlay `meta-xconn` at `meta-oe-alliance/meta-brands/meta-xconn`, then configure `MACHINE=xconn`, `DISTRO=openatv`. Build `oea-image` followed by `package-index`. Host prerequisites and upstream repositories remain governed by OE-Alliance's build documentation. No OpenBlackHole checkout, feed or sstate mirror is required.

## Validation and limitations

The receiver booted from XC slot 2. IPTV dependencies are being validated from this feed. Kernel, driver and recovery compatibility are device-specific. Image artifacts are not published here yet: existing local FULL/SLOT archives predate on-device fixes and must be rebuilt before release. Never flash an image or switch boot targets automatically as part of a package update.

## Update policy

Publish fixes only after building versioned IPKs and checking installation on the receiver. Update the package indexes after their payloads are uploaded and verified. Preserve old package versions for rollback. Keep source changes, package changes, and hardware-test coverage in release notes.

## Install the feed on an existing receiver

Download `scripts/install-feed.sh` to `/tmp`, inspect it, then run it as root on OpenATV 8.0.1 / xconn. It validates the image, checks GitHub index availability and backs up previous distro feed configuration before activating the independent feed. Third-party, settings and picon configurations are retained.

For BouquetMakerXtream the missing dependency observed on the receiver was `python3-multiprocessing`; install it with `opkg install python3-multiprocessing`. The image recipe now includes multiprocessing and requests for future images. This source change is not retroactively present in the original firmware archives.

Normal package payloads and indexes are under `feeds/openatv-8.0.1/xconn/{all,cortexa55,xconn}`. Two large optional debug packages are release assets under `feed-debug-8.0.1-20261125`, with their own opkg index. Package SHA256 values are included in each index.

Publishing a source change does not build an IPK automatically. Build and verify changed packages before replacing package files; publish payloads before the corresponding indexes. Do not perform a blanket system upgrade against the initial feed on a receiver with manually applied hotfixes.
