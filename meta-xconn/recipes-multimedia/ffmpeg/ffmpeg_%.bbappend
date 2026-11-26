# Preserve raw PCM and WAV output for standard audio clients.
EXTRA_OECONF:append = " --enable-muxer=pcm_s16le --enable-muxer=wav"
