"""Database download from the cloud (MongoDB), ported from libServer/downloadDB.py.

The cloud `library` database holds the library's records (book, marc, user, rentLog, rent).
A download makes the server's database match it: every table is compared with the cloud
and rows are added, changed or deleted, all in one transaction, in the database the server
works on (CLIB's own, C:\\CLIB\\Data, unless config.json names a copy).

The connection comes from config.json (never from the code, and never logged):
    "cloud": {"connection": "mongodb+srv://user:{}@host/...", "password": "...", "database": "library"}
or, to share libServer's settings instead of copying them:
    "cloud": {"libServerConfig": "C:\\\\Users\\\\me\\\\srcs\\\\libServer\\\\config.py"}
Without either, libServer's config.py next to this folder (..\\config.py) is used.
`connection` has a {} where the password goes, as in libServer.
"""
import datetime
import subprocess
from collections import OrderedDict, defaultdict
from pathlib import Path

from db import config, rows

# ---- field names: SQL column -> cloud field (libServer dbUtil.sql*Dict) ----------------

BOOK_MAP = {
    "SEQ": "seqnum", "BARCODE": "_id", "RFID": "rfid", "BOOKNAME": "title", "BOOKNUM": "num", "AUTHOR": "author",
    "TOTAL_NAME": "series", "CATEGORY": "category", "AUTHOR_CODE": "author_code", "CLAIMNUM": "claim_num",
    "COPYNUM": "copy_num", "EX_CATE": "ex_cate", "ISBN": "isbn", "PUBLISH": "publisher", "ATTACH": "attach",
    "CLAIM": "claim", "LOCATION": "location", "BOOKIN": "book_in", "REG_DATE": "registration_date",
    "MOD_DATE": "modification_date", "DELETE_YN": "deleted",
}
MARC_MAP = {"SEQ": "_id", "MARC_DATA": "MARC_DATA", "DELETE_YN": "DELETE_YN"}
USER_MAP = {
    "SEQ": "seqnum", "USER_CODE": "_id", "USER_NAME": "name", "PHONE_NUMBER": "phone", "ADDRESS": "address",
    "EMAIL": "email", "USER_LEVEL": "level", "USER_STATE": "state", "NOTICE": "memo", "USER_IMAGE": "image_path",
    "DISABLE_DATE": "disabled_until", "DELAY_DAY": "delayed_days", "DELAY_CHARGE": "delay_charge",
    "REG_DATE": "registration_date", "MOD_DATE": "modification_date", "DELETE_YN": "deleted",
}
RENT_MAP = {
    "SEQ": "_id", "BARCODE": "book_id", "STATS": "state", "USERS": "user_id", "LENT_DATE": "rent_date",
    "RETURN_DATE": "return_date", "RESERVE_USER": "reserve_user_id", "RESERVE_DATE": "reserve_date",
    "EXTEND_COUNT": "extend_count", "DELETE_YN": "deleted", "ATTACH": "attach", "ATTACH_USER": "attach_user",
}
HISTORY_MAP = {"SEQ": "_id", "BOOK_CODE": "book_id", "BOOK_STATE": "book_state", "USER_CODE": "user_id",
               "REG_DATE": "timestamp"}

# (result key, cloud collection, SQL table, key column, map). The `code` collection is not
# downloaded: libServer found that replacing CODE_SUB makes CLIB crash.
TABLES = [
    ("book", "book", "BOOK", "BARCODE", BOOK_MAP),
    ("marc", "marc", "MARC", "SEQ", MARC_MAP),
    ("user", "user", "USERS", "USER_CODE", USER_MAP),
    ("rentHistory", "rentLog", "RENTAL_HISTORY", "SEQ", HISTORY_MAP),
    ("rent", "rent", "BOOK_LENT", "BARCODE", RENT_MAP),
]
# Differences in these don't make a row "changed" (dbUtil.ignoreTag)
IGNORED = {"ATTACH", "ATTACH_USER"}
# libServer's own settings, used when config.json has no "cloud" connection
LIBSERVER_CONFIG = Path(__file__).resolve().parent.parent / "config.py"


def cloud_settings():
    cfg = dict(config().get("cloud") or {})
    shared_path = cfg.get("libServerConfig")
    if not shared_path and not cfg.get("connection") and LIBSERVER_CONFIG.exists():
        shared_path = LIBSERVER_CONFIG
    if shared_path:
        import runpy
        shared = runpy.run_path(str(shared_path)).get("Config") or {}
        for name in ("connection", "password", "key"):
            cfg.setdefault(name, shared.get(name))
    if not cfg.get("connection"):
        raise RuntimeError("클라우드 연결 정보가 없습니다.\nserver\\config.json의 \"cloud\"를 설정해주세요.")
    cfg.setdefault("database", "library")
    return cfg


def open_cloud():
    from pymongo import MongoClient
    cfg = cloud_settings()
    client = MongoClient(cfg["connection"].format(cfg.get("password") or ""), serverSelectionTimeoutMS=15000)
    return client, client[cfg["database"]]


# ---- MARC: the cloud keeps subfields after "\r" and ends fields with "\n" (libServer marc.py) --

CP = "cp949"


def _bytes(text):
    """CP949 bytes, an unencodable character becoming a space (MARC.decode)."""
    out = bytearray()
    for ch in text:
        try:
            out += ch.encode(CP)
        except UnicodeEncodeError:
            out += b" "
    return bytes(out)


class Marc:
    def __init__(self, data):
        raw = _bytes(data)
        self.header = raw[:24].decode(CP)
        rest = raw[24:]
        cut = rest.index(b"\n")
        directory, body = rest[:cut].decode(CP), rest[cut + 1:]
        self.fields = []  # [tag, data] for 005/008, [tag, indicator, [(code, value), ...]] otherwise
        for i in range(0, len(directory) - 11, 12):
            tag, size, offset = directory[i:i + 3], int(directory[i + 3:i + 7]), int(directory[i + 7:i + 12])
            text = body[offset:offset + size].decode(CP, errors="replace")
            if tag in ("005", "008"):
                self.fields.append([tag, text[:-1]])
                continue
            subs, code, value = [], None, ""
            j = 2
            while j < len(text):
                ch = text[j]
                if ch == "\r":
                    if code:
                        subs.append((code, value))
                    j += 1
                    code, value = (text[j] if j < len(text) else ""), ""
                elif ch == "\n":
                    break
                else:
                    value += ch
                j += 1
            if code:
                subs.append((code, value))
            self.fields.append([tag, text[:2], subs])

    def get(self, tag, code):
        for f in self.fields:
            if f[0] == tag and len(f) == 3:
                return next((v for c, v in f[2] if c == code), "").strip()
        return ""

    def check(self, barcode):
        """MARC.check(): children's books (HK0...) carry 아동 as 별치기호 (049 ▼f)."""
        if "HK0" not in barcode:
            return
        field = next((f for f in self.fields if f[0] == "049" and len(f) == 3), None)
        if field is None:
            return
        subs = OrderedDict(field[2])
        if subs.get("f") != "아동":
            subs["f"] = "아동"
            field[2] = list(subs.items())

    def encode(self):
        """The record as CLIB stores it: 0x1F subfields, 0x1E field ends, 0x1D at the end,
        lengths and offsets in CP949 bytes."""
        parts = []
        for f in self.fields:
            text = f[1] if len(f) == 2 else f[1] + "".join("\x1f" + c + v for c, v in f[2])
            parts.append(text + "\x1e")
        directory, offset = "", 0
        sizes = [len(_bytes(p)) for p in parts]
        for f, size in zip(self.fields, sizes):
            directory += f"{f[0]}{size:04}{offset:05}"
            offset += size
        base = len(self.header) + len(directory) + 1
        total = base + offset + 1
        return f"{total:05d}{self.header[5:12]}{base:05d}{self.header[17:]}{directory}\x1e{''.join(parts)}\x1d"

    def book_info(self):
        """MARC.getBookInfo(): the book's columns as the record has them."""
        stamp = next((f[1] for f in self.fields if f[0] == "005"), "")
        info = {"MOD_DATE": f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}, {stamp[8:10]}:{stamp[10:12]}:{stamp[12:14]}",
                "BARCODE": self.get("049", "l"), "EX_CATE": self.get("049", "f"), "ISBN": self.get("020", "a"),
                "BOOKNAME": self.get("245", "a"), "BOOKNUM": self.get("245", "n"), "AUTHOR": self.get("245", "d"),
                "CATEGORY": self.get("056", "a"), "PUBLISH": self.get("260", "b"), "TOTAL_NAME": self.get("440", "a"),
                "AUTHOR_CODE": self.get("090", "b"), "CLAIMNUM": self.get("090", "c"), "COPYNUM": self.get("049", "c")}
        info["CLAIM"] = "_".join(info[k] for k in ("EX_CATE", "CATEGORY", "AUTHOR_CODE", "CLAIMNUM", "COPYNUM")).strip()
        return info


# ---- download, compare, apply --------------------------------------------------

def to_sql(docs, field_map, key):
    """convertToSQL(): cloud documents keyed by the table's key column."""
    back = {v: k for k, v in field_map.items()}
    out = {}
    for doc in docs:
        row = {back[f]: v for f, v in doc.items() if f in back}
        if "ATTACH" in row and not row["ATTACH"]:
            row["ATTACH"] = "N"
        if key in row:
            out[row[key]] = row
    return out


def norm(value):
    return "" if value is None else str(value)


def compare(cloud, local):
    """compare(): keys to add, change and delete so the local table matches the cloud."""
    add, change = [], []
    for key, row in cloud.items():
        mine = local.get(key)
        if mine is None:
            add.append(key)
        elif any(c not in IGNORED and (c not in mine or norm(v) != norm(mine[c])) for c, v in row.items()):
            change.append(key)
    delete = [key for key in local if key not in cloud]
    return add, change, delete


def local_rows(conn, table, key, columns):
    have = {r["COLUMN_NAME"] for r in rows(conn, "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=?", table)}
    cols = [c for c in columns if c in have]
    return {r[key]: r for r in rows(conn, f"SELECT {', '.join(cols)} FROM {table}")}, have


def apply(conn, table, key, plan, cloud, have, progress):
    add, change, delete = plan
    cur = conn.cursor()
    done, total = 0, max(1, len(add) + len(change) + len(delete))

    def tick():
        nonlocal done
        done += 1
        if done % 200 == 0:
            progress(done * 100 // total)

    for k in delete:
        cur.execute(f"DELETE FROM {table} WHERE {key}=?", k)
        tick()
    for k in add:
        row = {c: v for c, v in cloud[k].items() if c in have}
        cur.execute(f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", *row.values())
        tick()
    for k in change:
        row = {c: v for c, v in cloud[k].items() if c in have and c != key}
        cur.execute(f"UPDATE {table} SET {', '.join(f'{c}=?' for c in row)} WHERE {key}=?", *row.values(), k)
        tick()
    cur.close()
    progress(100)


def download(conn, status, lock, test=False):
    """downloadDatabase(). status is updated as it goes, for the progress dialog:
    status["tables"][name] = {"count", "downloaded", "add", "change", "delete", "applied"}.
    The download itself runs unlocked; comparing and applying hold `lock` (the server's write
    lock) so no loan or return slips in between. Writes nothing when test is true; otherwise
    the caller commits. Returns the per-table result."""
    client, cloud_db = open_cloud()
    try:
        cloud = {}
        for name, coll, table, key, field_map in TABLES:
            entry = status["tables"][name]
            status["phase"] = f"{name} 내려받는 중"
            entry["count"] = cloud_db[coll].estimated_document_count()
            docs = []
            for doc in cloud_db[coll].find():
                docs.append(doc)
                if len(docs) % 500 == 0:
                    entry["downloaded"] = len(docs)
            entry["downloaded"] = len(docs)
            cloud[name] = to_sql(docs, field_map, key)
    finally:
        client.close()

    status["phase"] = "MARC 변환 중"
    books, marcs = cloud["book"], cloud["marc"]
    stats = {"same": 0, "changed": 0, "failed": 0}
    for barcode, book in books.items():
        marc = marcs.get(book.get("SEQ"))
        if not marc:
            continue
        original = marc.get("MARC_DATA") or ""
        # Records already in CLIB's form (0x1E field ends) are kept as they are; only the
        # older "\r"/"\n" form is converted
        if "\n" not in original and "\x1e" in original:
            stats["same"] += 1
            continue
        try:
            record = Marc(original)
            record.check(barcode)
            marc["MARC_DATA"] = record.encode()
            stats["same" if marc["MARC_DATA"] == original else "changed"] += 1
            info = record.book_info()
            if info["BARCODE"] == barcode:
                book.update(info)
        except (ValueError, IndexError, UnicodeError):
            stats["failed"] += 1
    status["marc"] = stats
    for user in cloud["user"].values():
        user.setdefault("DELETE_YN", "N")
    # Every book has a BOOK_LENT row; books the cloud has no rent for are on the shelf
    rents = cloud["rent"]
    for barcode, book in books.items():
        rents.setdefault(barcode, {"SEQ": book.get("SEQ"), "BARCODE": barcode, "STATS": 0, "USERS": "", "LENT_DATE": "",
                                   "RETURN_DATE": "", "RESERVE_USER": "", "RESERVE_DATE": "", "EXTEND_COUNT": 0,
                                   "DELETE_YN": book.get("DELETE_YN", "N"), "ATTACH": "N", "ATTACH_USER": ""})

    with lock:
        return _compare_and_apply(conn, status, cloud, test)


def _compare_and_apply(conn, status, cloud, test):
    status["phase"] = "비교 중"
    plans = {}
    for name, _, table, key, field_map in TABLES:
        mine, have = local_rows(conn, table, key, list(field_map))
        # An empty collection means something went wrong in the cloud, not "delete everything"
        if not cloud[name] and mine:
            raise RuntimeError(f"클라우드의 {name} 자료가 비어 있어 다운로드를 중단했습니다.")
        plans[name] = (table, key, compare(cloud[name], mine), have)
        add, change, delete = plans[name][2]
        status["tables"][name].update({"add": len(add), "change": len(change), "delete": len(delete)})

    result = {name: {k: status["tables"][name][k] for k in ("count", "add", "change", "delete")} for name in plans}
    if test:
        return result
    status["phase"] = "적용 중"
    for name, (table, key, plan, have) in plans.items():
        entry = status["tables"][name]
        apply(conn, table, key, plan, cloud[name], have, lambda p, e=entry: e.update(applied=p))
    return result


# ---- upload (libServer uploadDB.py) -------------------------------------------------

# Cloud fields a difference in doesn't count (dbUtil.ignoreTag)
UPLOAD_IGNORED = {"encrypted_email", "encrypted_phone", "modification_date", "attach", "attach_user"}


def to_cloud(local, field_map):
    """convertToMDB(): local rows -> cloud documents keyed by _id. A repeated _id gets a new
    one (makeUnique adds 100000000000), so no row is lost."""
    out = {}
    for row in local.values() if isinstance(local, dict) else local:
        doc = {field_map[c]: v for c, v in row.items() if c in field_map}
        key = doc.get("_id")
        while key in out and out[key] != doc:
            key = key + 100000000000 if isinstance(key, int) else f"{key}x"
        doc["_id"] = key
        out[key] = doc
    return out


def sign_contacts(users, key_pem):
    """encryptUserInfo(): each member's phone (digits only) and e-mail signed with the
    library's private key (RSA PKCS#1 v1.5, SHA-256, base64). Deleted members are skipped."""
    import base64
    import rsa
    key = rsa.PrivateKey.load_pkcs1(key_pem, "PEM")

    def sign(text):
        try:
            return base64.b64encode(rsa.sign(text.encode("ascii"), key, "SHA-256")).decode("ascii")
        except (UnicodeEncodeError, ValueError):
            return ""

    for user in users.values():
        if user.get("deleted") == "Y":
            continue
        phone = "".join(ch for ch in (user.get("phone") or "") if ch.isnumeric())
        email = user.get("email") or ""
        user["encrypted_phone"] = sign(phone) if phone else ""
        user["encrypted_email"] = sign(email) if email else ""


def compare_cloud(local, cloud):
    """compare() for an upload: keys to add, change and delete so the cloud matches."""
    add, change = [], []
    for key, doc in local.items():
        theirs = cloud.get(key)
        if theirs is None:
            add.append(key)
        elif any(f not in UPLOAD_IGNORED and (f not in theirs or norm(v) != norm(theirs[f])) for f, v in doc.items()):
            change.append(key)
    return add, change, [key for key in cloud if key not in local]


def push(collection, plan, docs, progress):
    """updateCloud(): inserts in hundreds, then deletes, then $set of every field."""
    from pymongo import DeleteOne, UpdateOne
    add, change, delete = plan
    total, done = max(1, len(add) + len(change) + len(delete)), 0
    for i in range(0, len(add), 100):
        collection.insert_many([docs[k] for k in add[i:i + 100]])
        done += len(add[i:i + 100])
        progress(done * 100 // total)
    ops = [DeleteOne({"_id": k}) for k in delete] + \
          [UpdateOne({"_id": k}, {"$set": {f: v for f, v in docs[k].items() if f != "_id"}}) for k in change]
    for i in range(0, len(ops), 500):
        collection.bulk_write(ops[i:i + 500], ordered=False)
        done += len(ops[i:i + 500])
        progress(done * 100 // total)
    progress(100)


def pair_returns(history):
    """checkRentHistory(checkRetDate=True): a checkout (state 1) followed by a return (state 0)
    of the same book gets the return's time as its return_date. Reservations (2) and other
    states don't break the pair; a lend of state 4 does, as in libServer. Sets return_date on
    the entries themselves and gives the ones whose return_date was missing or wrong."""
    by_book = defaultdict(list)
    for entry in history:
        by_book[entry.get("book_id")].append(entry)
    fixed = []
    for entries in by_book.values():
        entries.sort(key=lambda e: e.get("timestamp") or "")
        rented = None
        for entry in entries:
            state = str(entry.get("book_state"))
            if state not in ("0", "1", "4"):
                continue
            if (rented is not None and str(rented.get("book_state")) == "1" and state == "0"
                    and rented.get("return_date") != entry.get("timestamp")):
                rented["return_date"] = entry.get("timestamp")
                fixed.append(rented)
            rented = entry if state in ("1", "4") else None
    return fixed


def upload(conn, status, test=False, book_only=False):
    """uploadDatabase(): make the cloud match this server's database. Only 대출 rows for
    books that are out or reserved go up (the cloud has no rows for books on the shelf), and
    대출기록 also goes to the cloud's append-only rentHistory, where each returned checkout gets
    its return_date (as checkDB.py does). Changes nothing when test is true."""
    status["phase"] = "자료 읽는 중"
    local = {}
    for name, coll, table, key, field_map in TABLES:
        if book_only and name not in ("book", "marc"):
            continue
        mine, _ = local_rows(conn, table, key, list(field_map))
        docs = to_cloud(mine, field_map)
        if name == "rent":
            docs = {k: d for k, d in docs.items() if d.get("state") not in (0, "0")}
        if name == "user":
            sign_contacts(docs, cloud_settings().get("key") or "")
        local[name] = docs
        status["tables"][name]["local"] = len(docs)

    client, cloud_db = open_cloud()
    try:
        plans = {}
        for name, coll, *_ in TABLES:
            if name not in local:
                continue
            entry = status["tables"][name]
            status["phase"] = f"{name} 비교 중"
            entry["count"] = cloud_db[coll].estimated_document_count()
            theirs = {}
            for doc in cloud_db[coll].find():
                theirs[doc["_id"]] = doc
                if len(theirs) % 500 == 0:
                    entry["downloaded"] = len(theirs)
            entry["downloaded"] = len(theirs)
            # An empty local table means something is wrong here, not "empty the cloud"
            if not local[name] and theirs:
                raise RuntimeError(f"이 서버의 {name} 자료가 비어 있어 업로드를 중단했습니다.")
            plans[name] = compare_cloud(local[name], theirs)
            entry.update(add=len(plans[name][0]), change=len(plans[name][1]), delete=len(plans[name][2]))

        # rentHistory: an append-only copy of the history, matched on time, member, book and state,
        # whose checkouts also carry the date they were returned
        appended, returned = [], []
        if "rentHistory" in local:
            status["phase"] = "rentHistory 비교 중"
            history = list(cloud_db.rentHistory.find(
                {}, {"timestamp": 1, "user_id": 1, "book_id": 1, "book_state": 1, "return_date": 1}))
            seen = {(d.get("timestamp"), d.get("user_id"), d.get("book_id"), d.get("book_state")) for d in history}
            appended = [{k: v for k, v in d.items() if k != "_id"} for d in local["rentHistory"].values()
                        if (d.get("timestamp"), d.get("user_id"), d.get("book_id"), d.get("book_state")) not in seen]
            # New entries get their return_date before they go up; entries already in the cloud are updated
            returned = [d for d in pair_returns(history + appended) if "_id" in d]
            status["tables"]["rentHistory"]["appended"] = len(appended)
            status["tables"]["rentHistory"]["returned"] = len(returned)

        result = {name: {k: status["tables"][name].get(k) for k in ("local", "add", "change", "delete")} for name in plans}
        if "rentHistory" in result:
            result["rentHistory"]["appended"] = len(appended)
            result["rentHistory"]["returned"] = len(returned)
        if test:
            return result
        for name, coll, *_ in TABLES:
            if name in plans:
                status["phase"] = f"{name} 올리는 중"
                entry = status["tables"][name]
                push(cloud_db[coll], plans[name], local[name], lambda p, e=entry: e.update(applied=p))
        for i in range(0, len(appended), 100):
            cloud_db.rentHistory.insert_many(appended[i:i + 100])
        from pymongo import UpdateOne
        ops = [UpdateOne({"_id": d["_id"]}, {"$set": {"return_date": d["return_date"]}}) for d in returned]
        for i in range(0, len(ops), 500):
            cloud_db.rentHistory.bulk_write(ops[i:i + 500], ordered=False)
        return result
    finally:
        client.close()


def public_ip():
    """This host's public address, from api.ipify.org as in libServer; "" when unreachable."""
    import json
    import urllib.request
    try:
        with urllib.request.urlopen("https://api.ipify.org/?format=json", timeout=10) as response:
            return json.load(response).get("ip") or ""
    except (OSError, ValueError):
        return ""


def git_commit():
    """The checked-out commit. git may be missing from the server's PATH or refuse the folder
    (another user's checkout), so .git is read directly when it gives nothing."""
    here = Path(__file__).resolve().parent
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10,
                                cwd=here).stdout.strip()
        if commit:
            return commit
    except (OSError, subprocess.SubprocessError):
        pass
    git = next((d / ".git" for d in (here, *here.parents) if (d / ".git").is_dir()), None)
    if not git:
        return ""
    try:
        head = (git / "HEAD").read_text().strip()
        if not head.startswith("ref: "):
            return head
        ref = head[5:]
        if (git / ref).exists():
            return (git / ref).read_text().strip()
        for line in (git / "packed-refs").read_text().splitlines():
            if line.endswith(" " + ref):
                return line.split()[0]
    except OSError:
        pass
    return ""


def report_to_cloud(action, result):
    """reportServerLog(): note a download or upload in the cloud's serverLog."""
    entry = dict(result, action=action, time=str(datetime.datetime.now()), source="CLIB Web",
                 ip=public_ip(), commit=git_commit())
    client, cloud_db = open_cloud()
    try:
        cloud_db.serverLog.insert_one(entry)
    finally:
        client.close()
