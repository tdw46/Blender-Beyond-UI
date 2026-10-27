"""Per-host resource ownership; no shared registration or automatic timers."""


class Scope:
    def __init__(self):
        self._cleanup = []
        self.closed = False

    def own(self, cleanup):
        if self.closed:
            raise RuntimeError("Scope is closed")
        self._cleanup.append(cleanup)
        return cleanup

    def close(self):
        if self.closed:
            return
        self.closed = True
        errors = []
        while self._cleanup:
            try:
                self._cleanup.pop()()
            except Exception as error:
                errors.append(error)
        if errors:
            raise ExceptionGroup("Beyond UI cleanup failed", errors)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
