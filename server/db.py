"""Connection to CLIB's SQL Server LocalDB database.

CLIB Free keeps its data in C:\\CLIB\\Data\\CLIB.mdf, attached in (localdb)\\v11.0 as CLIB.
The server works on that database itself, under the same name, so CLIB, CLIB_Self and the
web share one set of data. LocalDB only takes local Windows connections, so this must run
under Windows Python. To work on a copy instead, set "dbPath" (and a "dbName" of its own,
e.g. CLIB_WEB) in config.json.
"""
import json
import os
from pathlib import Path

import pyodbc

HERE = Path(__file__).parent
DEFAULTS = {
    "dbPath": r"C:\CLIB\Data\CLIB.mdf",
    # the name CLIB and CLIB_Self open it by; the same file can't be attached under two names
    "dbName": "CLIB",
    "server": r"(localdb)\v11.0",
    # CLIB's install folder: CLIB.exe.Config settings and UserImage member photos
    "clibDir": r"C:\Program Files (x86)\CLIB\CLIB Free",
    # where photos chosen on the web are saved (the server can't write under Program Files)
    "photoDir": r"C:\CLIB\UserImage",
}


def config():
    """config.json (not in git) overrides the defaults; CLIB_DB overrides the path."""
    cfg = dict(DEFAULTS)
    path = HERE / "config.json"
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    if os.environ.get("CLIB_DB"):
        cfg["dbPath"] = os.environ["CLIB_DB"]
    return cfg


def driver():
    # Prefer the current driver; CLIB itself ships with Native Client 11.0
    names = pyodbc.drivers()
    for wanted in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server Native Client 11.0"):
        if wanted in names:
            return wanted
    raise RuntimeError(f"No SQL Server ODBC driver found (have: {names})")


# After LocalDB restarts (CLIB and CLIB_Self start it with "sqllocaldb s v11.0"), the driver
# can stop finding "(localdb)\\v11.0" by name although the instance runs fine; connecting to
# the instance's named pipe still works. The pipe changes with every restart, so it is looked
# up again whenever it fails.
_pipe = None


def localdb_pipe(server):
    """The named pipe of a LocalDB instance, starting the instance if it is stopped.
    sqllocaldb sometimes reports a running instance as stopped (and then fails to start a
    second one); the instance's own error.log still names the pipe it listens on."""
    import re
    import subprocess
    name = server.split("\\", 1)[1]
    for attempt in range(2):
        out = subprocess.run(["sqllocaldb", "info", name], capture_output=True, text=True, timeout=30).stdout
        found = re.search(r"(np:\\\\\.\\pipe\\\S+)", out)
        if found:
            return found.group(1)
        if attempt == 0:
            subprocess.run(["sqllocaldb", "start", name], capture_output=True, timeout=60)
    log = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Microsoft SQL Server Local DB" / "Instances" / name / "error.log"
    if log.exists():
        pipes = re.findall(r"accept connection on \[ (\\\\\.\\pipe\\[^\]\s]+) \]",
                           log.read_bytes().decode("utf-16-le", errors="ignore"))
        if pipes:
            return "np:" + pipes[-1]
    return None


def connect(master=False):
    """A connection to CLIB's database (attaching the file if LocalDB hasn't yet), or with
    master=True to the instance's master database, for BACKUP and RESTORE (autocommit, as those
    can't run in a transaction)."""
    global _pipe
    cfg = config()
    local = cfg["server"].lower().startswith("(localdb)\\")
    target = "Database=master;" if master else f"Database={cfg['dbName']};AttachDbFileName={cfg['dbPath']};"

    def attempt(server, timeout):
        return pyodbc.connect(
            f"Driver={{{driver()}}};Server={server};{target}Trusted_Connection=yes;",
            autocommit=master, timeout=timeout,
        )

    try:
        conn = attempt(_pipe or cfg["server"], 5 if local else 15)
    except pyodbc.Error:
        if not local:
            raise
        _pipe = localdb_pipe(cfg["server"])
        if not _pipe:
            raise
        conn = attempt(_pipe, 15)
    # CLIB stores Korean text in NVARCHAR columns
    conn.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-16le")
    conn.setencoding(encoding="utf-16le", ctype=pyodbc.SQL_WCHAR)
    return conn


def rows(conn, sql, *params):
    """Run a query and return a list of dicts."""
    cur = conn.cursor()
    cur.execute(sql, params)
    cols = [c[0] for c in cur.description]
    out = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    return out
