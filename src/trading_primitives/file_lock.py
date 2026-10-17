"""Lock esclusivo non bloccante su un file, compatibile Windows (msvcrt) e POSIX (flock).

Il sistema operativo rilascia il lock quando il processo termina, anche in modo brusco: nessun PID da
interpretare e nessun processo da terminare. Due handle dello stesso processo si escludono a vicenda.
"""

from __future__ import annotations

import os


class FileLock:
    def __init__(self, path) -> None:
        self.path = os.fspath(path)
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def acquire(self) -> bool:
        """True se il lock è stato preso ora; False se è già tenuto da un altro handle o processo."""
        if self._fd is not None:
            raise RuntimeError("lock già tenuto da questo oggetto")
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        fd, self._fd = self._fd, None
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
