"""Translate receive events into balanced Enigma2 make/repeat/long/break events."""
class KeyFlow:
    # IR repeats are generated locally (like the kernel's input autorepeat) while
    # the remote keeps sending frames; they stop once no frame arrived for
    # hold_gap, so releasing the button does not keep moving the cursor.
    def __init__(self, emit, delay=0.25, rate=0.05, long_delay=0.8, hold_gap=0.15):
        self.emit = emit
        self.delay, self.rate, self.long_delay, self.hold_gap = delay, rate, long_delay, hold_gap
        self.held = None

    def release(self):
        held, self.held = self.held, None
        if held:
            self.emit(held['code'], 1)

    def event(self, token, code, value, now):
        if value == 0:
            if self.held and self.held['token'] == token:
                self.release()
            return
        if value not in (1, 2):
            return
        if value == 1 or not self.held or self.held['token'] != token:
            self.release()
            bt = token.startswith('bt:')
            self.held = dict(token=token, code=code, started=now, seen=now, bt=bt,
                             repeated=now, long=False, timeout=2.0 if bt else 0.28)
            self.emit(code, 0)
            return
        held = self.held
        held['seen'] = now
        self.repeat(now)

    def repeat(self, now):
        held = self.held
        if now-held['started'] >= self.long_delay and not held['long']:
            held['long'] = True
            self.emit(held['code'], 3)
        if self.held is not held or now-held['started'] < self.delay:
            return
        if held['bt']:
            if now-held['repeated'] >= 0.10:
                held['repeated'] = now
                self.emit(held['code'], 2)
        elif now-held['seen'] <= self.hold_gap and now-held['repeated'] >= self.rate:
            # keep the average period at rate even with a coarser poll timer
            held['repeated'] = max(held['repeated'] + self.rate, now - self.rate)
            self.emit(held['code'], 2)

    def expire(self, now):
        if self.held and now-self.held['seen'] > self.held['timeout']:
            self.release()
        elif self.held and not self.held['bt']:
            self.repeat(now)
