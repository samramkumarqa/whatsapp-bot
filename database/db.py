import sqlite3
import queue
import threading

CRM_DB = "data/app.db"

CONVERSATION_DB = "conversations.db"

_POOL_SIZE = 5


class _PooledConnection:
    """
    Thin wrapper around a real sqlite3.Connection.

    Every call site in this codebase follows the same pattern:

        conn = get_crm_connection() / get_conversation_connection()
        ... conn.execute(...) / conn.commit() ...
        conn.close()

    Previously get_*_connection() opened a brand new OS-level sqlite
    connection on every single call, and the matching conn.close() tore
    it down again - real overhead (file open, PRAGMA setup) repeated for
    every query anywhere in the app.

    This wrapper hands out a connection from a small pool and makes
    close() return it to the pool instead of actually closing it.
    Everything else (execute, commit, cursor, row_factory, ...) is
    forwarded straight through to the real connection via __getattr__,
    so none of the ~100 existing call sites need to change.
    """

    def __init__(self, conn, pool):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_pool", pool)
        object.__setattr__(self, "_closed", False)

    def close(self):
        if not self._closed:
            object.__setattr__(self, "_closed", True)
            self._pool.put(self._conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        setattr(self._conn, name, value)

    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._conn.__exit__(exc_type, exc_val, exc_tb)


class _ConnectionPool:
    """
    A small bounded pool of real sqlite3 connections for one DB file.

    Connections are created lazily (up to `size`) and reused afterwards.
    Since callers can run on different threads (e.g. FastAPI's threadpool
    for sync routes, or run_in_threadpool for async ones), connections are
    opened with check_same_thread=False - safe here because SQLite's WAL
    mode (set on every connection below) allows concurrent readers and a
    single writer, and each checked-out connection is only ever used by
    one caller at a time.
    """

    def __init__(self, db_path, size=_POOL_SIZE):
        self.db_path = db_path
        self._pool = queue.Queue(maxsize=size)
        self._size = size
        self._created = 0
        self._lock = threading.Lock()

    def _make_connection(self):
        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def get(self):
        try:
            conn = self._pool.get_nowait()
        except queue.Empty:
            conn = None
            with self._lock:
                if self._created < self._size:
                    conn = self._make_connection()
                    self._created += 1
            if conn is None:
                # All connections are checked out - wait for one to free up
                # instead of unboundedly opening more.
                conn = self._pool.get()
        return _PooledConnection(conn, self._pool)

    def put(self, conn):
        self._pool.put(conn)


_crm_pool = _ConnectionPool(CRM_DB)
_conversation_pool = _ConnectionPool(CONVERSATION_DB)


def get_crm_connection():
    return _crm_pool.get()


def get_conversation_connection():
    return _conversation_pool.get()


def execute_crm(query, params=()):

    conn = get_crm_connection()

    cursor = conn.execute(query, params)

    conn.commit()

    conn.close()

    return cursor


def fetchone_crm(query, params=()):

    conn = get_crm_connection()

    row = conn.execute(
        query,
        params
    ).fetchone()

    conn.close()

    return row


def fetchall_crm(query, params=()):

    conn = get_crm_connection()

    rows = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return rows


def execute_conversation(query, params=()):

    conn = get_conversation_connection()

    cursor = conn.execute(query, params)

    conn.commit()

    conn.close()

    return cursor


def fetchone_conversation(query, params=()):

    conn = get_conversation_connection()

    row = conn.execute(
        query,
        params
    ).fetchone()

    conn.close()

    return row


def fetchall_conversation(query, params=()):

    conn = get_conversation_connection()

    rows = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return rows

def commit_and_close(conn):
    conn.commit()
    conn.close()


def close_connection(conn):
    conn.close()