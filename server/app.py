"""CLIB Web local server: a JSON API over CLIB's database, and two web apps that use it:
    http://127.0.0.1:8080/  ../web       the library's app (CLIB.exe)
    http://127.0.0.1:8081/  ../web-self  the self-service kiosk (CLIB_Self.exe)
Both ports serve the same /api, in one process, so writes from either share one lock.

Run with the Windows venv (LocalDB only accepts local Windows connections):
    .venv\\Scripts\\python app.py

Reads get their own connection, which is rolled back. Lending, returns and renewals
(circulation.py) run one at a time in a transaction that commits only when they succeed.
Set "readOnly": true in config.json to refuse all writes.
"""
import threading
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_file, send_from_directory

import backup
import circulation
import records
import repo
import settings_store
from db import config, connect

WEB = Path(__file__).resolve().parent.parent / "web"
WEB_SELF = Path(__file__).resolve().parent.parent / "web-self"
# Which web app each port serves; the API is the same on all of them
SITES = {8080: WEB, 8081: WEB_SELF}
app = Flask(__name__, static_folder=None)
app.json.ensure_ascii = False


# LocalDB falls over when hundreds of connections open at once (a page firing one request
# per member crashed the server); let at most a few run together and queue the rest
DB_SLOTS = threading.BoundedSemaphore(8)


@contextmanager
def db():
    with DB_SLOTS:
        conn = connect()
        try:
            yield conn
        finally:
            conn.rollback()  # reads never commit
            conn.close()


WRITE_LOCK = threading.Lock()
READ_ONLY_MESSAGE = {"error": "서버가 읽기 전용으로 설정되어 있어 저장할 수 없습니다.\n(config.json의 readOnly)"}
last_daily = {"date": None}


def read_only():
    return bool(config().get("readOnly"))


def write(fn, *args):
    """Run one circulation operation: commit if it succeeded, roll back otherwise."""
    if read_only():
        return READ_ONLY_MESSAGE
    with WRITE_LOCK, DB_SLOTS:
        conn = connect()
        try:
            result = fn(conn, *args)
            if result.get("ok"):
                conn.commit()
            else:
                conn.rollback()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# While a backup is being restored the database is cut off; other requests are turned away
MAINTENANCE = {"on": False}


@app.before_request
def maintenance():
    if MAINTENANCE["on"] and request.path.startswith("/api/") and not request.path.startswith("/api/backup"):
        return jsonify({"error": "데이터 복구 중입니다. 잠시 후 다시 시도해주세요."}), 503


@app.before_request
def daily_checks():
    """CLIB runs CheckDelayBooks / ReservationBooks / CheckUsers when it starts; do the same
    once a day, before the first request that needs current loan states."""
    if not request.path.startswith("/api/") or read_only() or last_daily["date"] == date.today():
        return
    with WRITE_LOCK:
        if last_daily["date"] == date.today():
            return
        conn = connect()
        try:
            result = circulation.daily_checks(conn)
            conn.commit()
            app.logger.info("daily checks: %s", result)
        finally:
            conn.close()
        last_daily["date"] = date.today()
        # A new day for a server that keeps running is like CLIB starting that day: 자동백업 when due
        if backup.auto_backup_due("start"):
            threading.Thread(target=backup.auto_backup, daemon=True).start()


# ---- API ------------------------------------------------------------------

@app.get("/api/meta")
def meta():
    with db() as conn:
        cfg = config()
        return jsonify({"readOnly": read_only(), "database": cfg["dbPath"], "today": repo.today(),
                        "settings": repo.settings(conn)})


@app.get("/api/users/next")
def next_user():
    with db() as conn:
        by_grade = repo.settings(conn)["userCodeByGrade"]
        return jsonify(records.next_user_id(conn, request.args.get("grade", ""), by_grade))


@app.post("/api/users/batch")
def users_batch():
    """Several members in one request and one connection (회원검색 → 불러오기)."""
    ids = (request.get_json(force=True).get("ids") or [])[:2000]
    with db() as conn:
        return jsonify([u for u in (repo.find_user(conn, i) for i in ids) if u])


@app.get("/api/users/deleted")
def deleted_users():
    """삭제한 회원번호관리"""
    with db() as conn:
        return jsonify(repo.deleted_users(conn))


@app.get("/api/users/<user_id>/photo")
def user_photo(user_id):
    with db() as conn:
        path = repo.user_photo(conn, user_id)
    # Not cached: the same address shows a new photo once one is saved
    return send_file(path, max_age=0) if path else ("", 404)


@app.post("/api/users/<user_id>/photo")
def save_user_photo(user_id):
    """회원관리 저장 with a photo chosen by 파일찾기 (the image is the request body)."""
    return jsonify(write(records.save_photo, user_id, request.get_data()))


@app.get("/api/users/<user_id>/history")
def user_history(user_id):
    """이용내역 조회"""
    with db() as conn:
        found = repo.user_history(conn, user_id)
        return jsonify(found) if found else (jsonify(None), 404)


@app.get("/api/users/<user_id>")
def user(user_id):
    with db() as conn:
        found = repo.find_user(conn, user_id)
        return jsonify(found) if found else (jsonify(None), 404)


@app.get("/api/users")
def users():
    with db() as conn:
        if "name" in request.args:
            return jsonify(repo.users_by_name(conn, request.args["name"]))
        if "grade" in request.args:
            return jsonify(repo.users_by_grade(conn, request.args["grade"]))
        return jsonify(repo.search_users(conn, request.args.get("field", "회원번호"), request.args.get("q", "")))


@app.get("/api/books/<barcode>")
def book(barcode):
    with db() as conn:
        found = repo.find_book(conn, barcode, full=request.args.get("full") == "1")
        return jsonify(found) if found else (jsonify(None), 404)


@app.post("/api/books/batch")
def books_batch():
    """Several books in one request and one connection (도서 불러오기 → 도서관리)."""
    body = request.get_json(force=True)
    with db() as conn:
        return jsonify(repo.find_books(conn, (body.get("barcodes") or [])[:2000], full=bool(body.get("full"))))


@app.post("/api/books/marcfile")
def marc_file():
    """파일로 저장 > Marc 파일 저장: the checked books' MARC records as one CP949 file."""
    body = request.get_json(force=True)
    with db() as conn:
        data, count = records.marc_file(conn, (body.get("items") or [])[:20000], bool(body.get("crlf")))
    return Response(data, mimetype="application/octet-stream", headers={"X-Record-Count": str(count)})


@app.get("/api/overdue")
def overdue():
    """연체관리"""
    with db() as conn:
        return jsonify(repo.overdue(conn))


@app.get("/api/stats/books")
def stats_books():
    """도서보유현황: ?by=0..4 (도서상태, 도서분류, 별치기호, 소장위치, 반입구분)."""
    with db() as conn:
        return jsonify(repo.book_stats(conn, int(request.args.get("by", 0))))


@app.get("/api/stats/books/detail")
def stats_books_detail():
    """The books of one 도서보유현황 row: ?by=&name=&row= (row: its position, for 도서분류)."""
    with db() as conn:
        return jsonify(repo.book_stats_detail(conn, int(request.args.get("by", 0)), request.args.get("name", "전체"),
                                              int(request.args.get("row", 0))))


@app.get("/api/stats/users")
def stats_users():
    """이용자현황: ?by=0 (회원등급) or 1 (회원상태)."""
    with db() as conn:
        return jsonify(repo.user_stats(conn, int(request.args.get("by", 0))))


@app.get("/api/stats/users/detail")
def stats_users_detail():
    with db() as conn:
        return jsonify(repo.user_stats_detail(conn, int(request.args.get("by", 0)), request.args.get("name", "전체")))


@app.get("/api/search")
def kiosk_search():
    """The kiosk's 도서검색: field 전체/서명/저자/출판사/등록번호/총서명/발행년도, or none for every book."""
    with db() as conn:
        return jsonify(repo.kiosk_search(conn, request.args.get("field"), request.args.get("q", "")))


@app.get("/api/books")
def books():
    a = request.args
    with db() as conn:
        if "start" in a or "end" in a:
            return jsonify(repo.search_books(conn, start=a.get("start"), end=a.get("end")))
        return jsonify(repo.search_books(conn, a.get("field", "서명"), a.get("q", "")))


@app.get("/api/loans")
def loans():
    with db() as conn:
        return jsonify(repo.all_loans(conn))


@app.get("/api/reservations")
def reservations():
    with db() as conn:
        return jsonify(repo.all_reservations(conn))


@app.get("/api/history")
def history():
    a = request.args
    with db() as conn:
        return jsonify(repo.history(conn, a.get("from", repo.today()), a.get("to", repo.today())))


# ---- lending, returns, renewals ----------------------------------------------

@app.post("/api/lend")
def lend():
    body = request.get_json(force=True)
    return jsonify(write(circulation.lend, body.get("userId", ""), body.get("barcode", ""), body.get("answers") or {}))


@app.post("/api/return")
def return_book():
    body = request.get_json(force=True)
    return jsonify(write(circulation.return_book, body.get("barcode", ""), body.get("answers") or {}))


@app.post("/api/extend")
def extend():
    body = request.get_json(force=True)
    return jsonify(write(circulation.extend, body.get("barcode", "")))


@app.post("/api/reserve")
def reserve():
    body = request.get_json(force=True)
    return jsonify(write(circulation.reserve, body.get("userId", ""), body.get("barcode", "")))


@app.post("/api/reserve/cancel")
def cancel_reserve():
    body = request.get_json(force=True)
    return jsonify(write(circulation.cancel_reserve, body.get("userId", ""), body.get("barcode", "")))


# ---- members and books ----------------------------------------------------------

@app.post("/api/users")
def save_user():
    body = request.get_json(force=True)
    return jsonify(write(records.save_user, body.get("user") or {}, body.get("answers") or {}))


@app.post("/api/users/delete")
def delete_user():
    body = request.get_json(force=True)
    return jsonify(write(records.delete_user, body.get("userId", "")))


@app.post("/api/users/paycharge")
def pay_charge():
    body = request.get_json(force=True)
    return jsonify(write(records.pay_charge, body.get("userId", "")))


@app.post("/api/users/renumber")
def renumber_user():
    body = request.get_json(force=True)
    return jsonify(write(records.renumber_user, body.get("userId", ""), body.get("grade", ""), body.get("answers") or {}))


@app.post("/api/users/purge")
def purge_user():
    body = request.get_json(force=True)
    return jsonify(write(records.purge_user, body.get("userId", ""), body.get("deleteDate", "")))


@app.post("/api/users/restore")
def restore_user():
    body = request.get_json(force=True)
    return jsonify(write(records.restore_user, body.get("userId", "")))


@app.post("/api/books")
def save_book():
    body = request.get_json(force=True)
    return jsonify(write(records.save_book, body.get("book") or {}, body.get("original"), body.get("answers") or {}))


@app.post("/api/books/delete")
def delete_book():
    body = request.get_json(force=True)
    return jsonify(write(records.delete_book, body.get("barcode", "")))


# ---- settings -------------------------------------------------------------------

@app.post("/api/settings")
def save_settings():
    import settings_store
    body = request.get_json(force=True)
    result = write(settings_store.save_settings, body.get("changes") or {})
    if result.get("ok"):
        # CLIB.exe.Config values go to clib_settings.json, only once the database part committed
        if result.get("config"):
            settings_store.write_overlay(result["config"])
        with db() as conn:
            result = {"ok": True, "settings": repo.settings(conn)}
    return jsonify(result)


# ---- 데이터백업 / 데이터복구 / 자동백업설정 (backup.py) -------------------------------------

@app.get("/api/backup")
def backups():
    return jsonify({"options": backup.options(), "runs": backup.RUNS, "files": backup.list_backups(),
                    "folders": {"backup": str(backup.folder_path("backup")), "auto": backup.CLIB_AUTO_DIR},
                    "database": config()["dbName"]})


@app.post("/api/backup")
def make_backup():
    """데이터백업: a new .bak in the backup folder (reads only, so allowed when read-only)."""
    return jsonify(backup.manual_backup())


@app.get("/api/backup/file")
def backup_file():
    path = backup.file_path(request.args.get("folder", ""), request.args.get("name", ""))
    if not path:
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name, mimetype="application/octet-stream")


@app.post("/api/backup/upload")
def upload_backup():
    """A .bak from the browser (request body), kept in the backup folder for 데이터복구."""
    if not (request.args.get("name") or "").lower().endswith(".bak"):
        return jsonify({"error": "백업 파일(*.bak)을 선택해주세요."})
    return jsonify(backup.save_upload(request.stream, request.args["name"]))


@app.post("/api/backup/restore")
def restore_backup():
    if read_only():
        return jsonify(READ_ONLY_MESSAGE)
    body = request.get_json(force=True)
    with WRITE_LOCK:
        MAINTENANCE["on"] = True
        try:
            result = backup.restore(body.get("folder", ""), body.get("name", ""))
        finally:
            MAINTENANCE["on"] = False
    if result.get("ok"):
        last_daily["date"] = None  # the restored data gets CLIB's daily checks again
    return jsonify(result)


@app.post("/api/backup/options")
def backup_options():
    """자동백업설정. As in CLIB, turning it on (확인) makes a backup right away."""
    result = backup.save_options(request.get_json(force=True))
    if result.get("ok") and result["options"]["auto"]:
        backup.auto_backup()
        result["options"] = backup.options()
    return jsonify(result)


@app.errorhandler(Exception)
def failed(e):
    if hasattr(e, "code"):  # HTTP errors such as 404 keep their status
        return jsonify({"error": str(e)}), e.code
    app.logger.exception(e)
    return jsonify({"error": f"서버 오류: {e}"}), 500


# ---- cloud download (데이터베이스 관리) -----------------------------------------------

# One cloud job (download or upload) at a time, run in the background; the dialogs poll
# GET for progress
CLOUD = {"state": "idle"}
CLOUD_LOCK = threading.Lock()
CLOUD_TABLES = ("book", "marc", "user", "rentHistory", "rent")
# The last real (not test) download and upload, kept in clib_settings.json across restarts
CLOUD_LAST = {"download": "CLOUD_LAST_DOWNLOAD", "upload": "CLOUD_LAST_UPLOAD"}


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def now_text():
    return datetime.now().strftime(TIME_FORMAT)


def cloud_job(mode, test, book_only):
    import cloud
    status = CLOUD
    conn = connect()
    try:
        if mode == "download":
            result = cloud.download(conn, status, WRITE_LOCK, test)
            if not test:
                conn.commit()
        else:
            # The cloud has no transaction: an upload that fails midway can be run again
            result = cloud.upload(conn, status, test, book_only)
        status["phase"] = "완료"
        if not test:
            settings_store.write_overlay({CLOUD_LAST[mode]: now_text()})
            try:
                cloud.report_to_cloud("Download DB" if mode == "download" else "Upload DB", result)
            except Exception as e:  # the data went through; only the cloud log failed
                status["warning"] = f"클라우드 기록 실패: {type(e).__name__}"
        status.update(state="done", result=result, finishedAt=now_text())
    except Exception as e:
        conn.rollback()
        message = str(e)
        try:  # never show the password, whatever the driver put in its message
            secret = cloud.cloud_settings().get("password")
            if secret:
                message = message.replace(secret, "***")
        except Exception:
            pass
        status.update(state="error", error=message[:500], finishedAt=now_text())
    finally:
        conn.rollback()  # an upload only reads; a finished download is already committed
        conn.close()


def start_cloud_job(mode):
    body = request.get_json(silent=True) or {}
    test = bool(body.get("test"))
    if mode == "download" and not test and read_only():
        return jsonify(READ_ONLY_MESSAGE)
    with CLOUD_LOCK:
        if CLOUD.get("state") == "running":
            what = "다운로드" if CLOUD.get("mode") == "download" else "업로드"
            return jsonify({"error": f"이미 클라우드 {what}가 진행중입니다."}), 409
        CLOUD.clear()
        CLOUD.update(state="running", mode=mode, test=test, bookOnly=bool(body.get("bookOnly")), phase="연결 중",
                     startedAt=now_text(),
                     tables={name: {} for name in CLOUD_TABLES})
    threading.Thread(target=cloud_job, args=(mode, test, bool(body.get("bookOnly"))), daemon=True).start()
    return jsonify({"ok": True})


@app.post("/api/cloud/download")
def cloud_download():
    """Make this server's database match the cloud; {"test": true} only compares."""
    return start_cloud_job("download")


@app.post("/api/cloud/upload")
def cloud_upload():
    """Make the cloud match this server's database; {"test": true} only compares,
    {"bookOnly": true} sends only books and MARC."""
    return start_cloud_job("upload")


@app.get("/api/cloud")
@app.get("/api/cloud/download")
def cloud_status():
    """The current job (startedAt, finishedAt, elapsed seconds) and the last real download / upload."""
    status = dict(CLOUD)
    if status.get("startedAt"):
        end = datetime.strptime(status["finishedAt"], TIME_FORMAT) if status.get("finishedAt") else datetime.now()
        status["elapsed"] = int((end - datetime.strptime(status["startedAt"], TIME_FORMAT)).total_seconds())
    saved = settings_store.overlay()
    status["last"] = {mode: saved.get(key, "") for mode, key in CLOUD_LAST.items()}
    return jsonify(status)


# ---- the web app ------------------------------------------------------------

def site():
    return SITES.get(int(request.environ.get("SERVER_PORT") or 8080), WEB)


@app.get("/")
def index():
    return send_from_directory(site(), "index.html")


@app.get("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        abort(404)
    return send_from_directory(site(), path)


if __name__ == "__main__":
    import socket
    import sys

    # Windows lets a second server bind the same port, and requests then go to whichever
    # it likes (an old copy keeps answering with old code); refuse to start instead
    from werkzeug.serving import make_server

    for port in SITES:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                sys.exit(f"포트 {port}을 이미 다른 프로그램(이미 실행 중인 서버?)이 사용하고 있습니다.")
    # Local machine only: there is no login yet
    servers = [make_server("127.0.0.1", port, app, threaded=True) for port in SITES]
    for port, root in SITES.items():
        print(f" * {root.name}: http://127.0.0.1:{port}/", flush=True)
    for server in servers[1:]:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    # CLIB backs up when it starts and exits (DefaultBackup, and 자동백업 when due); so does the server
    threading.Thread(target=backup.run_triggers, args=("start",), daemon=True).start()
    try:
        servers[0].serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print(" * 종료 전 백업 중…", flush=True)
        backup.run_triggers("stop")
