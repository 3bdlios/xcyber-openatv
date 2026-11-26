IMAGE_INSTALL:append = " xc-hardware xc-gui-startup xc-wifi xc-hdmi-route xc-remote-timing xc-video-route xc-gst-video xc-frontpanel xc-subtitle-overlay-compat xc-audiod xc-volume-bridge xc-video-setup xc-screenshot xc-multiboot-menu alsa-plugins alsa-utils-aplay gstreamer1.0-plugins-base-volume gstreamer1.0-plugins-good-mpg123 gstreamer1.0-libav ffmpeg enigma2-plugin-systemplugins-serviceapp exteplayer3 gstplayer2 enigma2-plugin-extensions-mediaplayer enigma2-plugin-extensions-enhancedmoviecenter enigma2-plugin-extensions-dvdplayer"

# Dependencies needed by IPTV playlist plugins.
IMAGE_INSTALL:append = " python3-multiprocessing python3-requests"

IMAGE_INSTALL:append = " xc-password-pam-fix"

IMAGE_INSTALL:append = " xc-image-name"
