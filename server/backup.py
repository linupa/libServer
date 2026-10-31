"""데이터백업 / 데이터복구 / 자동백업설정, ported from BookDream.DataBackUp(), AutoBackup(),
DefaultBackup(), Set_Backup and DataRestore.exe.

Backups are SQL Server .bak files made with BACKUP DATABASE, as CLIB makes them, so CLIB's
own DataRestore.exe can restore what the web backs up and the other way round. They are
written by LocalDB itself, on this PC:

- 데이터백업 and 자동백업: the backup folder (자동백업설정's 백업위치, C:\\CLIB\\Backup by default)
- CLIB's own safety copies, made whenever it starts or exits (yyyyMMdd_ON.bak / _OFF.bak,
  the latest 20 kept): C:\\CLIB\\Data\\AutoBackup. The server makes them when it starts and stops.

Restoring replaces the whole database. Every other connection (CLIB, the kiosk, the server's
own requests) is cut off first, and the current data is backed up before it is replaced.
"""
import re
from datetime import date, datetime
from pathlib import Path

from db import config, connect

DEFAULT_DIR = r"C:\CLIB\Backup"
CLIB_AUTO_DIR = r"C:\CLIB\Data\AutoBackup"
# 백업시점 (BACKUPRUN): 0 실행 및 종료시, 1 실행시, 2 종료시
RUNS = ("CLIB 실행 및 종료시", "CLIB 실행시", "CLIB 종료시")
FOLDERS = {"backup": "백업 폴더", "auto": "CLIB 자동 백업"}
NAME = re.compile(r"^[\w\-. ()가-힣]+\.bak$", re.IGNORECASE)


def database():
    name = config()["dbName"]
    if not re.fullmatch(r"\w+", name):
        raise ValueError(f"데이터베이스 이름이 올바르지 않습니다: {name}")
    return name


# ---- 자동백업설정 (CLIB keeps these in its user settings; here in clib_settings.json) ----

def options():
    import settings_store
    o = settings_store.overlay()
    num = lambda k, d: int(o[k]) if str(o.get(k, "")).strip().isdigit() else d
    return {"auto": o.get("AUTOBACKUP") == "1", "path": o.get("BACKUPPATH") or DEFAULT_DIR,
            "days": num("BACKUPDATE", 15), "run": min(num("BACKUPRUN", 0), 2), "last": o.get("LAST", "")}


def save_options(values):
    """Set_Backup.btn_ok_Click(). Returns { error } or { ok, options }."""
    import settings_store
    days = str(values.get("days", "")).strip()
    if not days.isdigit():
        return {"error": "백업주기는 숫자만 입력할 수 있습니다."}
    path = (values.get("path") or "").strip() or DEFAULT_DIR
    if not re.match(r"^[A-Za-z]:\\", path):
        return {"error": "백업위치는 이 PC의 폴더 경로(예: C:\\CLIB\\Backup)로 입력해주세요."}
    run = int(values.get("run") or 0)
    settings_store.write_overlay({"AUTOBACKUP": "1" if values.get("auto") else "0", "BACKUPPATH": path,
                                  "BACKUPDATE": int(days), "BACKUPRUN": run if run in (0, 1, 2) else 0})
    return {"ok": True, "options": options()}


# ---- backing up -------------------------------------------------------------------

def folder_path(folder):
    return Path(options()["path"] if folder == "backup" else CLIB_AUTO_DIR)


def backup_to(path):
    """BACKUP DATABASE <db> TO DISK=<path>. WITH INIT: a file of the same name is replaced, not
    appended to (CLIB checks that the name is new instead)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connect().close()  # makes sure LocalDB has the database file attached
    conn = connect(master=True)
    try:
        cur = conn.cursor()
        cur.execute(f"BACKUP DATABASE [{database()}] TO DISK=? WITH INIT", str(path))
        while cur.nextset():  # BACKUP reports its progress as messages; wait for all of them
            pass
        cur.close()
    finally:
        conn.close()
    return path


def stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def manual_backup():
    """데이터백업: yyyyMMdd_HHmmss.bak in the backup folder."""
    path = backup_to(folder_path("backup") / f"{stamp()}.bak")
    return {"ok": True, "folder": "backup", "name": path.name, "size": path.stat().st_size}


def auto_backup():
    """AutoBackup(): one backup a day in the backup folder; an earlier one from today is
    replaced. CLIB deletes every file of the day there (its manual backups too); here only
    the automatic ones (_auto) go."""
    folder = folder_path("backup")
    today = datetime.now().strftime("%Y%m%d_")
    if folder.exists():
        for f in folder.glob(f"{today}*_auto.bak"):
            try:
                f.unlink()
            except OSError:
                pass
    path = backup_to(folder / f"{stamp()}_auto.bak")
    import settings_store
    settings_store.write_overlay({"LAST": date.today().isoformat()})
    return path


def auto_backup_due(trigger):
    """BookDream_Load / FormClosing: trigger 'start' or 'stop'. 자동백업 runs when it is on, the
    백업시점 includes this moment, and the 백업주기 has passed since the last one (or the last
    one was today, which CLIB refreshes)."""
    o = options()
    if not o["auto"] or o["days"] <= 0 or o["run"] not in ((0, 1) if trigger == "start" else (0, 2)):
        return False
    last = o["last"] or date.today().isoformat()
    try:
        days = (date.today() - date.fromisoformat(last[:10])).days
    except ValueError:
        days = 0
    return days == 0 or days >= o["days"]


def default_backup(trigger):
    """DefaultBackup(): CLIB's safety copy whenever it starts (_ON) or exits (_OFF), in
    C:\\CLIB\\Data\\AutoBackup. With 20 files there, the two oldest go first."""
    folder = Path(CLIB_AUTO_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    files = sorted(folder.glob("*.bak"))
    if len(files) >= 20:
        for f in files[:2]:
            f.unlink(missing_ok=True)
    return backup_to(folder / f"{datetime.now():%Y%m%d}_{'ON' if trigger == 'start' else 'OFF'}.bak")


def run_triggers(trigger, log=print):
    """What CLIB does when it starts or exits: the safety copy, then 자동백업 if it is due."""
    for name, job in (("default", lambda: default_backup(trigger)),
                      ("auto", lambda: auto_backup() if auto_backup_due(trigger) else None)):
        try:
            done = job()
            if done:
                log(f"backup ({name}, {trigger}): {done}")
        except Exception as e:  # a failed backup must not stop the server
            log(f"backup ({name}, {trigger}) failed: {e}")


def list_backups():
    out = []
    for folder in FOLDERS:
        path = folder_path(folder)
        if not path.is_dir():
            continue
        for f in path.glob("*.bak"):
            st = f.stat()
            out.append({"folder": folder, "place": FOLDERS[folder], "name": f.name, "size": st.st_size,
                        "time": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
    return sorted(out, key=lambda b: b["time"], reverse=True)


def file_path(folder, name):
    """A backup file in one of the two folders; None for anything else."""
    if folder not in FOLDERS or not NAME.match(name or "") or "/" in name or "\\" in name:
        return None
    path = folder_path(folder) / name
    return path if path.is_file() else None


def save_upload(stream, filename):
    """A .bak sent from the browser, kept in the backup folder so it can be restored."""
    stem = re.sub(r"[^\w\-.가-힣]", "_", Path(filename or "backup.bak").stem)[:60] or "backup"
    folder = folder_path("backup")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"upload_{stamp()}_{stem}.bak"
    with open(path, "wb") as out:
        while chunk := stream.read(1 << 20):
            out.write(chunk)
    return {"ok": True, "folder": "backup", "name": path.name, "size": path.stat().st_size}


# ---- restoring ----------------------------------------------------------------------

def restore(folder, name):
    """DataRestore.button2_Click(): replace the database with a backup. CLIB drops the database
    and restores it where the backup says its files were; here it is restored over the
    database in place (WITH REPLACE), its files moved to where this database keeps them, so a
    backup made elsewhere (another PC, CLIB_WEB) restores too. The current data is backed up
    first (…_before_restore.bak in the backup folder)."""
    path = file_path(folder, name)
    if not path:
        return {"error": "백업 파일을 찾을 수 없습니다."}
    db_name = database()
    conn = connect(master=True)
    try:
        cur = conn.cursor()
        try:
            cur.execute("RESTORE FILELISTONLY FROM DISK=?", str(path))
            backup_files = [(r.LogicalName, r.Type) for r in cur.fetchall()]
        except Exception:
            return {"error": "백업 파일을 읽을 수 없습니다.\nCLIB 백업 파일(.bak)인지 확인해주세요."}
        connect().close()  # attach the database so its files are known
        current = {}
        for r in cur.execute("SELECT type_desc, physical_name FROM sys.master_files WHERE database_id = DB_ID(?)", db_name).fetchall():
            current.setdefault("D" if r.type_desc == "ROWS" else "L", r.physical_name)
        if set(t for _, t in backup_files) - set(current) or not current:
            return {"error": "백업 파일의 구성이 현재 데이터베이스와 맞지 않습니다."}
        before = backup_to(folder_path("backup") / f"{stamp()}_before_restore.bak")

        moves = " ".join(", MOVE ? TO ?" for _ in backup_files)
        params = [str(path)]
        for logical, kind in backup_files:
            params += [logical, current[kind]]
        failed = None
        cur.execute(f"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        try:
            cur.execute(f"RESTORE DATABASE [{db_name}] FROM DISK=? WITH REPLACE{moves}", *params)
            while cur.nextset():
                pass
        except Exception as e:
            failed = e
        finally:
            try:
                cur.execute(f"ALTER DATABASE [{db_name}] SET MULTI_USER")
            except Exception:
                pass
        cur.close()
    finally:
        conn.close()
    if failed:
        return {"error": f"복구하지 못했습니다.\n{failed}\n복구 전 데이터는 {before.name} 에 백업되어 있습니다."}
    return {"ok": True, "before": before.name}
