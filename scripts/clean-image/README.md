# Clean receiver snapshot packaging

These tools package a snapshot of the working OpenATV receiver, rather than rebuilding old IPKs over manually applied fixes. They never write to a physical disk.

Set `XC_PROJECT_ROOT` to the independent build project and `XC_SNAPSHOT_DIR` to a private working directory. The clean OE-produced rootfs tar is used only for factory configuration defaults. The boot and recovery inputs come from the currently working XC boot chain; no OpenBH checkout, partition or repository is read.

Capture root files with GNU tar using `--one-file-system --numeric-owner`. Exclude virtual mounts, BOOT, STORAGE, `/etc/enigma2`, `/home/root`, SSH keys, network credentials, cam accounts, EPG imports and the AudioShift plugin. Capture only the required XC boot files separately. Keep captures private.

Extract captures into `root/` and `boot/` under a single saved fakeroot metadata database. Run `sanitize.py`, then `verify-root.py`, then `package.py` under that same fakeroot database. Do not copy the input archives or working root into a public repository.

The tools remove AudioShift and its helper, subscriptions, channel/tuner state, DHCP history, network backups and host identities. They restore clean OE defaults, enable the setup wizard, keep GitHub package feeds, reserve `/media/hdd` for STORAGE, and generate a fresh hybrid GPT/MBR IMG with XC recovery. Newly formatted sparse files avoid carrying deleted data from an earlier image.

Checks cover root ownership, EXT4 consistency, required plugins and kernel modules, absence of AudioShift, empty IPTV entries, recovery state schema, partition payload hashes and full gzip decompression hash. The generated image still needs a fresh-media hardware boot test.
