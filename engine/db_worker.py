from __future__ import annotations

import threading
import queue
from pathlib import Path
from typing import Callable, Any

from .db import connect_db


class DBWorker:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._queue: "queue.Queue[tuple[Callable, tuple, dict]]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop_event = threading.Event()
        self._errors: list[str] = []
        self._errors_lock = threading.Lock()
        self._thread.start()

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Enqueue a callable to run on the DB worker.

        The callable will be invoked as func(conn, *args, **kwargs) where conn
        is a fresh sqlite3.Connection from `connect_db(self.db_path)`.
        """
        self._queue.put((func, args, kwargs))

    def _run(self) -> None:
        conn = connect_db(self.db_path)
        # Configure WAL and synchronous for better write performance
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
        try:
            while not self._stop_event.is_set() or not self._queue.empty():
                try:
                    func, args, kwargs = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                try:
                    func(conn, *args, **kwargs)
                    conn.commit()
                except Exception:
                    # Don't let DB errors kill the worker; log and persist trace.
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    try:
                        import traceback

                        tb = traceback.format_exc()
                        with self._errors_lock:
                            self._errors.append(tb)
                        try:
                            with open(self.db_path.parent / "db_worker_errors.log", "a", encoding="utf-8") as fh:
                                fh.write(tb + "\n---\n")
                        except Exception:
                            pass
                    except Exception:
                        pass
                finally:
                    self._queue.task_done()
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def stop(self, wait: bool = True) -> None:
        self._stop_event.set()
        if wait:
            self._thread.join()

    def flush(self, timeout: float | None = None) -> None:
        """Block until the queue is empty (or timeout)."""
        try:
            self._queue.join()
        except Exception:
            pass

    def last_errors(self) -> list[str]:
        with self._errors_lock:
            return list(self._errors)
