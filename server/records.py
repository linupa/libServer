"""Saving and deleting members and books, ported from CLIB's Users.SaveUsers() / DeleteUsers()
and BookManage.SaveMarcDB() / DeleteMarcDB(), including the MARC record CLIB keeps per book.

Same result shapes as circulation.py: { error } | { confirm, title, ask } | { ok, ... }.
"""
import re
from datetime import datetime

from circulation import execute, next_seq, one
from db import rows

FT, SF, RT = "\x1e", "\x1f", "\x1d"


def stamp():
    # USERS / BOOK REG_DATE and MOD_DATE use CLIB's "yyyy-MM-dd, HH:mm:ss"
    return datetime.now().strftime("%Y-%m-%d, %H:%M:%S")


def code_of(conn, number, name):
    r = one(conn, "SELECT SUB_CODE FROM CODE_SUB WHERE CODE_NUMBER=? AND SUB_NAME=?", number, (name or "").strip())
    return r["SUB_CODE"] if r else None


# ---- members ---------------------------------------------------------------

def next_user_id(conn, grade_name, by_grade):
    """Users.NewUser(). Numbering by grade: the grade's 구분기호 + the highest number after it + 1,
    keeping its width. One shared sequence: the highest member number + 1; when that number
    has letters (AB0635), they stay and the digits after them count up (AB0636)."""
    g = one(conn, """SELECT G.CLASSIFY FROM USER_LEVEL G JOIN CODE_SUB C ON C.CODE_NUMBER='000'
                     AND C.SUB_CODE=G.CODE_NUMBER WHERE C.SUB_NAME = ?""", grade_name)
    prefix = (g["CLASSIFY"] or "").strip() if g else ""
    if not by_grade or not prefix:
        top = one(conn, "SELECT MAX(USER_CODE) AS m FROM USERS")["m"]
        if not top:
            return "00000001"
        top = top.strip()
        if top.isdigit():
            # CLIB also subtracts the grade prefix's length from the width here; that drops digits
            return str(int(top) + 1).zfill(len(top))
        if re.search(r"[가-힣ㄱ-ㆎ]", top):
            return prefix + "00000001"
        m = re.match(r"^(\D*)(\d+)$", top)
        if not m:
            return prefix + "00000001"
        return m.group(1) + str(int(m.group(2)) + 1).zfill(len(m.group(2)))
    codes = [r["USER_CODE"].strip() for r in rows(conn, "SELECT USER_CODE FROM USERS WHERE SUBSTRING(USER_CODE, 1, ?) = ?",
                                                  len(prefix), prefix)]
    nums = [(int(c[len(prefix):]), len(c) - len(prefix)) for c in codes if c[len(prefix):].isdigit()]
    if not nums:
        return prefix + "00000001"
    n, width = max(nums)
    return prefix + str(n + 1).zfill(width)


def save_user(conn, record, answers):
    """Users.SaveUsers(). record: userId, userName, userGrade, userState, phone, address, email,
    memo, and isNew (the screen was making a new member)."""
    user_id = (record.get("userId") or "").strip().upper()
    if not user_id:
        return {"error": "회원번호를 입력해주세요."}
    if re.search(r"[가-힣ㄱ-ㆎ]", user_id) or not re.fullmatch(r"[A-Z0-9]+", user_id):
        return {"error": "회원번호는 영어와 숫자만 가능합니다."}
    if not (record.get("userName") or "").strip():
        return {"error": "회원명을 입력해주세요."}
    level = one(conn, """SELECT CODE_NUMBER FROM USER_LEVEL WHERE CODE_NUMBER =
                         (SELECT SUB_CODE FROM CODE_SUB WHERE CODE_NUMBER='000' AND SUB_NAME=?)""",
                (record.get("userGrade") or "").strip())
    if not level:
        return {"error": "회원등급이 잘못되었습니다."}
    state = code_of(conn, "003", record.get("userState")) or 0

    # A number used by a deleted member can be reused once its old records are removed
    if one(conn, "SELECT COUNT(*) AS n FROM USERS WHERE DELETE_YN='Y' AND USER_CODE=?", user_id)["n"]:
        if "deletedCode" not in answers:
            return {"confirm": "삭제된 회원번호입니다.\n이전 기록을 삭제 후 사용하시겠습니까?\n※ 이전 기록을 삭제 후 회원번호를 재사용하는 경우,\n삭제된 기록은 복구할 수 없습니다.",
                    "title": "회원번호 재사용", "ask": "deletedCode"}
        if not answers["deletedCode"]:
            return {"cancelled": True}
    existing = one(conn, "SELECT SEQ, DELAY_CHARGE, USER_IMAGE FROM USERS WHERE USER_CODE=? AND DELETE_YN='N'", user_id)
    # CLIB asks on every save of an existing number; here only when the screen was making a new member
    if existing and record.get("isNew") and "overwrite" not in answers:
        return {"confirm": "동일한 회원번호가 이미 존재합니다.\n덮어쓰겠습니까?", "title": "회원번호중복", "ask": "overwrite"}
    if existing and record.get("isNew") and not answers["overwrite"]:
        return {"cancelled": True}

    if answers.get("deletedCode"):
        execute(conn, "DELETE FROM USERS WHERE DELETE_YN='Y' AND USER_CODE=?", user_id)
        execute(conn, "DELETE FROM RENTAL_HISTORY WHERE USER_CODE=?", user_id)
    values = [(record.get(k) or "").strip() for k in ("userName", "phone", "address", "email")]
    memo = "\n".join(l for l in (record.get("memo") or "").split("\n") if not l.startswith("대출정지일 :")).strip()
    if existing:
        # 연체금 isn't shown on this install's screen, so the stored amount is kept;
        # going back to 정상 clears the suspension date as in CLIB
        sql = """UPDATE USERS SET USER_NAME=?, PHONE_NUMBER=?, ADDRESS=?, EMAIL=?, USER_LEVEL=?, USER_STATE=?,
                 NOTICE=?, MOD_DATE=?""" + (", DISABLE_DATE=''" if state == 0 else "") + " WHERE USER_CODE=? AND DELETE_YN='N'"
        execute(conn, sql, *values, level["CODE_NUMBER"], state, memo, stamp(), user_id)
    else:
        execute(conn, """INSERT INTO USERS (SEQ,USER_CODE,USER_NAME,PHONE_NUMBER,ADDRESS,EMAIL,USER_LEVEL,USER_STATE,NOTICE,
                         USER_IMAGE,DISABLE_DATE,DELAY_DAY,DELAY_CHARGE,REG_DATE,MOD_DATE,DELETE_YN)
                         VALUES (?,?,?,?,?,?,?,?,?,'','',0,0,?,'','N')""",
                next_seq(conn, "USERS"), user_id, *values, level["CODE_NUMBER"], state, memo, stamp())
    return {"ok": True, "userId": user_id, "created": not existing}


def delete_user(conn, user_id):
    """Users.DeleteUsers(): refused while the member has books, reservations or attachments out;
    otherwise marked deleted (DELETE_YN='Y') and taken off any waiting list."""
    user_id = (user_id or "").strip().upper()
    if not one(conn, "SELECT USER_CODE FROM USERS WHERE USER_CODE=? AND DELETE_YN='N'", user_id):
        return {"error": "해당하는 회원이 없습니다."}
    if one(conn, "SELECT COUNT(*) AS n FROM BOOK_LENT WHERE DELETE_YN='N' AND USERS=?", user_id)["n"]:
        return {"error": "현재 대출중인 도서가 있습니다.\n도서를 반납 후 삭제해주세요."}
    if one(conn, "SELECT COUNT(*) AS n FROM RESERVATION WHERE USER_CODE=?", user_id)["n"]:
        return {"error": "현재 예약중인 도서가 있습니다.\n예약을 취소 후 삭제해주세요."}
    if one(conn, "SELECT COUNT(*) AS n FROM BOOK_LENT WHERE ATTACH_USER=?", user_id)["n"]:
        return {"error": "현재 대출중인 딸림자료가 있습니다.\n자료를 반납 후 삭제해주세요."}
    execute(conn, "UPDATE USERS SET DELETE_YN='Y', MOD_DATE=? WHERE USER_CODE=? AND DELETE_YN='N'", stamp(), user_id)
    execute(conn, "UPDATE BOOK_LENT SET RESERVE_USER='' WHERE RESERVE_USER=?", user_id)
    execute(conn, "DELETE FROM RESERVATION WHERE USER_CODE=?", user_id)
    return {"ok": True}


# The first bytes of the image types CLIB's photo box takes
IMAGE_MAGIC = {b"\xff\xd8": "jpg", b"\x89PNG": "png", b"GIF8": "gif", b"BM": "bmp"}


def save_photo(conn, user_id, data):
    """Users.SaveUsers()'s photo: the picture chosen with 파일찾기 is saved as <회원번호>.<ext>
    and USER_IMAGE holds its full path (CLIB copies it into its UserImage folder; the web
    saves into photoDir, which CLIB reads the same way)."""
    from db import config
    from pathlib import Path
    user_id = (user_id or "").strip().upper()
    if not one(conn, "SELECT USER_CODE FROM USERS WHERE USER_CODE=? AND DELETE_YN='N'", user_id):
        return {"error": "회원을 먼저 저장해주세요."}
    ext = next((e for magic, e in IMAGE_MAGIC.items() if data.startswith(magic)), None)
    if not ext:
        return {"error": "사진은 JPG, PNG, GIF, BMP 파일만 사용할 수 있습니다."}
    if len(data) > 10 * 1024 * 1024:
        return {"error": "사진 파일이 너무 큽니다. (10MB 이하)"}
    folder = Path(config()["photoDir"])
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{user_id}.{ext}"
    # A photo saved before under another type would be picked up instead of this one
    for old in folder.glob(f"{user_id}.*"):
        if old != path and old.suffix.lower().lstrip(".") in ("jpg", "jpeg", "png", "gif", "bmp"):
            old.unlink(missing_ok=True)
    path.write_bytes(data)
    execute(conn, "UPDATE USERS SET USER_IMAGE=?, MOD_DATE=? WHERE USER_CODE=? AND DELETE_YN='N'", str(path), stamp(), user_id)
    return {"ok": True, "photo": str(path)}


def pay_charge(conn, user_id):
    """Users.btn_charge_Click() (연체금 완납): the unpaid 연체금 goes to 0 and the member is 연체중
    while books are still overdue, otherwise 정상 (which ends a suspension, as saving does)."""
    user_id = (user_id or "").strip().upper()
    if not one(conn, "SELECT USER_CODE FROM USERS WHERE USER_CODE=? AND DELETE_YN='N'", user_id):
        return {"error": "해당하는 회원이 없습니다."}
    late = one(conn, "SELECT COUNT(*) AS n FROM BOOK_LENT WHERE DELETE_YN='N' AND STATS=3 AND USERS=?", user_id)["n"]
    execute(conn, "UPDATE USERS SET DELAY_CHARGE=0, USER_STATE=?, MOD_DATE=?" + ("" if late else ", DISABLE_DATE=''") +
            " WHERE USER_CODE=? AND DELETE_YN='N'", 1 if late else 0, stamp(), user_id)
    return {"ok": True}


def renumber_user(conn, user_id, grade_name, answers):
    """UserCodeDlg.ReUserCode(): give a member the grade's next number (its 구분기호 and the
    highest number after it + 1, deleted members included, as 신규 numbers by grade). Their
    loans, attachments, reservations and history move with them."""
    user_id = (user_id or "").strip().upper()
    if not one(conn, "SELECT USER_CODE FROM USERS WHERE USER_CODE=? AND DELETE_YN='N'", user_id):
        return {"error": "해당하는 회원이 없습니다."}
    new_id = next_user_id(conn, grade_name, True)
    if "renumber" not in answers:
        return {"confirm": f"회원번호를 변경하시겠습니까?\n기존 : {user_id}\n변경 : {new_id}", "title": "회원번호", "ask": "renumber"}
    if not answers["renumber"]:
        return {"cancelled": True}
    if one(conn, "SELECT COUNT(*) AS n FROM USERS WHERE USER_CODE=?", new_id)["n"]:
        return {"error": "이미 사용중인 회원번호입니다."}
    execute(conn, "UPDATE USERS SET USER_CODE=? WHERE DELETE_YN='N' AND USER_CODE=?", new_id, user_id)
    for column in ("USERS", "ATTACH_USER", "RESERVE_USER"):
        execute(conn, f"UPDATE BOOK_LENT SET {column}=? WHERE DELETE_YN='N' AND {column}=?", new_id, user_id)
    for table in ("RENTAL_HISTORY", "RESERVATION", "ATTACH_HISTORY"):
        execute(conn, f"UPDATE {table} SET USER_CODE=? WHERE USER_CODE=?", new_id, user_id)
    return {"ok": True, "userId": new_id}


def purge_user(conn, user_id, delete_date):
    """DeleteUsers.DeleteUserCode(): remove a deleted member for good, with the history recorded
    up to its deletion (delete_date is its MOD_DATE as listed)."""
    user_id = (user_id or "").strip().upper()
    if not one(conn, "SELECT COUNT(*) AS n FROM USERS WHERE DELETE_YN='Y' AND USER_CODE=?", user_id)["n"]:
        return {"error": "해당하는 회원이 없습니다."}
    until = (delete_date or "").replace(",", "")
    execute(conn, "DELETE FROM USERS WHERE DELETE_YN='Y' AND USER_CODE=?", user_id)
    execute(conn, "DELETE FROM RENTAL_HISTORY WHERE USER_CODE=? AND REG_DATE <= ?", user_id, until)
    return {"ok": True}


def restore_user(conn, user_id):
    """DeleteUsers.ReUseUserCode(): bring a deleted member back, unless the number is in use."""
    user_id = (user_id or "").strip().upper()
    if one(conn, "SELECT COUNT(*) AS n FROM USERS WHERE DELETE_YN='N' AND USER_CODE=?", user_id)["n"]:
        return {"error": "이미 해당번호를 다른 회원이 사용중입니다."}
    # CLIB restores every deleted row with the number; only the latest comes back here, so a
    # number deleted twice doesn't turn into two members
    found = one(conn, "SELECT MAX(SEQ) AS s FROM USERS WHERE DELETE_YN='Y' AND USER_CODE=?", user_id)
    if not found or found["s"] is None:
        return {"error": "해당하는 회원이 없습니다."}
    execute(conn, "UPDATE USERS SET DELETE_YN='N' WHERE SEQ=? AND DELETE_YN='Y'", found["s"])
    return {"ok": True}


# ---- MARC --------------------------------------------------------------------

def marc_parse(data):
    """ISO 2709 -> (leader, [[tag, body], ...]). Fields come in directory order, split on the
    field terminator (CLIB's directory lengths count CP949 bytes)."""
    head, _, body = (data or "").partition(FT)
    tags = [head[i:i + 3] for i in range(24, len(head) - 11, 12)]
    return head[:24], [[t, b] for t, b in zip(tags, body.rstrip(RT).split(FT))]


def marc_template():
    """BookManage.NewMarc(): the record a new book starts from."""
    now = datetime.now()
    blank = lambda *codes: "  " + "".join(f"{SF}{c} " for c in codes)
    return "00000namk   00000 k 4500", [
        ["005", now.strftime("%Y%m%d%H%M%S")],
        ["008", now.strftime("%y%m%d") + "s        ulka          000a  kor  "],
        ["020", blank("a", "c")], ["049", "0 " + f"{SF}l {SF}c "], ["090", blank("a", "b", "c")],
        ["100", "1 " + f"{SF}a "], ["245", "00" + f"{SF}a "], ["260", blank("a", "b", "c")],
        ["300", blank("a", "c", "e")], ["950", "0 " + f"{SF}b\\"],
    ]


def marc_set(fields, tag, indicators, code, value):
    """BookManage.ModifyExpertEdit(): replace a subfield's text, add the subfield to the field,
    or add the field in tag order."""
    for f in fields:
        if f[0] == tag:
            parts = f[1].split(SF)
            for i, p in enumerate(parts[1:], 1):
                if p[:1] == code:
                    parts[i] = code + value
                    f[1] = SF.join(parts)
                    return
            f[1] += SF + code + value
            return
    at = next((i for i, f in enumerate(fields) if f[0].isdigit() and int(f[0]) >= int(tag)), len(fields))
    fields.insert(at, [tag, indicators.replace("_", " ") + SF + code + value])


def marc_build(leader, fields):
    """BookManage.CreateMarc(): directory lengths and offsets in CP949 bytes, record length and
    base address written into the leader."""
    size = lambda s: len(s.encode("cp949", errors="replace"))
    directory, data, pos = "", "", 0
    for tag, body in fields:
        chunk = body + FT
        directory += f"{tag}{size(chunk):04d}{pos:05d}"
        pos += size(chunk)
        data += chunk
    directory += FT
    data += RT
    leader = (leader + " " * 24)[:24]
    base = len(leader) + len(directory)
    return f"{base + size(data):05d}" + leader[5:12] + f"{base:05d}" + leader[17:] + directory + data


# Form field -> (tag, indicators, subfield), as BookManage's TextChanged handlers write them
MARC_MAP = {
    "isbn": [("020", "__", "a")], "price": [("020", "__", "c"), ("950", "0_", "b")],
    "barcode": [("049", "0_", "l")], "claimVolume": [("049", "0_", "v"), ("090", "__", "c")],
    "copy": [("049", "0_", "c")], "exCate": [("049", "0_", "f")],
    "category": [("056", "__", "a"), ("090", "__", "a")], "authorCode": [("090", "__", "b")],
    # title and volume before author, so a new 245 reads ▼a … ▼n … ▼d … like CLIB's records
    "title": [("245", "0_", "a")], "volume": [("245", "0_", "n")], "author": [("100", "1_", "a"), ("245", "0_", "d")],
    "pubPlace": [("260", "__", "a")], "publisher": [("260", "__", "b")], "year": [("260", "__", "c")],
    "pages": [("300", "__", "a")], "size": [("300", "__", "c")], "attach": [("300", "__", "e")],
}


def marc_update(old_marc, record, before):
    """Apply the fields that changed since the record was read (before) to the book's MARC,
    keeping everything else, as editing in CLIB's form does."""
    leader, fields = marc_parse(old_marc) if old_marc else marc_template()
    if not fields:
        leader, fields = marc_template()
    for key, targets in MARC_MAP.items():
        value = (record.get(key) or "").strip()
        if old_marc and value == (before.get(key) or "").strip():
            continue
        for tag, ind, code in targets:
            marc_set(fields, tag, ind, code, value)
    # 총서명 (440 ▼a, with 청구권차 as ▼v); an empty 총서명 removes the field
    series = (record.get("seriesTitle") or "").strip()
    if not old_marc or series != (before.get("seriesTitle") or "").strip() or \
            (record.get("claimVolume") or "") != (before.get("claimVolume") or ""):
        if series:
            marc_set(fields, "440", "00", "a", series)
            if (record.get("claimVolume") or "").strip():
                marc_set(fields, "440", "00", "v", record["claimVolume"].strip())
        else:
            fields = [f for f in fields if f[0] != "440"]
    # ModifyDate(): 005 is the time of the save
    for f in fields:
        if f[0] == "005":
            f[1] = datetime.now().strftime("%Y%m%d%H%M%S")
    return marc_build(leader, fields)


def marc_file(conn, items, crlf):
    """SaveFileProcess.SaveMarcFileThFn(): the records of the books checked in 도서관리, one after
    another, each ending with the record terminator and, with CRLF, a line break between them;
    written in CP949 as CLIB's Encoding.Default. items: [{original, record}]. A saved book
    (record None) gives its stored record; an edited or new one is written with its changes, as
    the list's MARC column holds them in CLIB."""
    import repo
    out = []
    for item in items:
        original = (item.get("original") or "").strip().upper()
        record = item.get("record")
        stored = ""
        if original:
            r = one(conn, "SELECT M.MARC_DATA FROM BOOK B JOIN MARC M ON M.SEQ=B.SEQ "
                          "WHERE B.BARCODE=? AND B.DELETE_YN='N' AND M.DELETE_YN='N'", original)
            stored = (r or {}).get("MARC_DATA") or ""
        if record:
            before = (repo.find_book(conn, original, full=True) or {}) if stored else {}
            marc = marc_update(stored, record, before)
        else:
            marc = stored
        if marc:
            out.append(marc if marc.endswith(RT) else marc + RT)
    return ("\r\n" if crlf else "").join(out).encode("cp949", errors="replace"), len(out)


# ---- books -------------------------------------------------------------------

def save_book(conn, record, original, answers):
    """BookManage.SaveMarcDB() (and the 등록번호 변경 path). record holds the form fields;
    original is the barcode the book had when it was opened (None for a new book)."""
    import repo
    barcode = (record.get("barcode") or "").strip().upper()
    for key, msg in (("title", "도서명을 입력해주세요"), ("author", "저자명을 입력해주세요"),
                     ("category", "분류기호를 입력해주세요"), ("authorCode", "저자기호를 입력해주세요"),
                     ("barcode", "등록번호를 입력해주세요")):
        if not (record.get(key) or "").strip():
            return {"error": msg, "title": "필수항목 누락"}
    location = code_of(conn, "002", record.get("location"))
    if location is None:
        return {"error": "소장위치 선택이 잘못되었습니다."}
    book_in = code_of(conn, "004", record.get("bookIn")) or 0
    state = code_of(conn, "001", record.get("state"))
    if state is None:
        state = 0
    original = (original or "").strip().upper() or None

    # 등록번호 변경: the book keeps its records under the new number
    if original and original != barcode:
        if "changeCode" not in answers:
            return {"confirm": f"등록번호를 변경하시겠습니까?\n변경 전 : {original}\n변경 후 : {barcode}",
                    "title": "등록번호 변경", "ask": "changeCode"}
        if not answers["changeCode"]:
            return {"cancelled": True}
        if one(conn, "SELECT COUNT(*) AS n FROM BOOK WHERE DELETE_YN='N' AND BARCODE=?", barcode)["n"]:
            return {"error": "이미 사용중인 등록번호입니다."}

    target = original or barcode
    current = one(conn, "SELECT B.SEQ, B.REG_DATE, L.USERS, L.RESERVE_USER, L.STATS FROM BOOK B JOIN BOOK_LENT L ON L.SEQ=B.SEQ "
                        "WHERE B.BARCODE=? AND B.DELETE_YN='N' AND L.DELETE_YN='N'", target)
    if current and not original and "overwrite" not in answers:
        return {"confirm": "동일한 등록번호의 도서가 있습니다.\n정보를 덮어쓰기 하시겠습니까?", "title": "등록번호 중복", "ask": "overwrite"}
    if current and not original and not answers["overwrite"]:
        return {"cancelled": True}
    if current and state not in (1, 2, 3):
        if (current["USERS"] or "").strip():
            return {"error": "대출자가 있는 도서입니다.\n반납처리를 하신 후 상태를 변경해주세요."}
        if (current["RESERVE_USER"] or "").strip():
            return {"error": "예약자가 있는 도서입니다.\n예약취소를 하신 후 상태를 변경해주세요."}

    # A barcode left by a deleted book is cleared before it is used again
    if not current:
        old = [r["SEQ"] for r in rows(conn, "SELECT SEQ FROM BOOK WHERE DELETE_YN='Y' AND BARCODE=?", barcode)]
        for seq in old:
            for table in ("BOOK", "MARC", "BOOK_LENT"):
                execute(conn, f"DELETE FROM {table} WHERE DELETE_YN='Y' AND SEQ=?", seq)
        if old:
            execute(conn, "DELETE FROM RENTAL_HISTORY WHERE BOOK_CODE=?", barcode)
            execute(conn, "DELETE FROM BARCODE_UID WHERE BARCODE=?", barcode)

    if original and original != barcode:
        for sql in ("UPDATE BOOK SET BARCODE=? WHERE SEQ=? AND DELETE_YN='N'", "UPDATE BOOK_LENT SET BARCODE=? WHERE SEQ=?"):
            execute(conn, sql, barcode, current["SEQ"])
        for table, col in (("RENTAL_HISTORY", "BOOK_CODE"), ("BARCODE_UID", "BARCODE"), ("ATTACH_HISTORY", "BOOK_CODE"),
                           ("RESERVATION", "BOOK_CODE")):
            execute(conn, f"UPDATE {table} SET {col}=? WHERE {col}=?", barcode, original)

    f = lambda k: (record.get(k) or "").strip()
    claim = "_".join([f("exCate"), f("category"), f("authorCode"), f("claimVolume"), f("copy")])
    columns = [f("uid"), f("title"), f("author"), f("seriesTitle"), f("category"), f("authorCode"), f("claimVolume"),
               f("copy"), f("exCate"), f("isbn"), f("publisher"), f("attach"), claim, location, book_in, f("volume")]
    if current:
        before = repo.find_book(conn, barcode, full=True) or {}
        if original and original != barcode:
            before["barcode"] = original  # the MARC still says the old number (049 ▼l)
        old_marc = (one(conn, "SELECT MARC_DATA FROM MARC WHERE SEQ=?", current["SEQ"]) or {}).get("MARC_DATA") or ""
        marc = marc_update(old_marc, record, before)
        execute(conn, """UPDATE BOOK SET RFID=?, BOOKNAME=?, AUTHOR=?, TOTAL_NAME=?, CATEGORY=?, AUTHOR_CODE=?, CLAIMNUM=?,
                         COPYNUM=?, EX_CATE=?, ISBN=?, PUBLISH=?, ATTACH=?, CLAIM=?, LOCATION=?, BOOKIN=?, BOOKNUM=?, MOD_DATE=?
                         WHERE SEQ=?""", *columns, stamp(), current["SEQ"])
        if one(conn, "SELECT COUNT(*) AS n FROM MARC WHERE SEQ=?", current["SEQ"])["n"]:
            execute(conn, "UPDATE MARC SET MARC_DATA=? WHERE SEQ=?", marc, current["SEQ"])
        else:
            execute(conn, "INSERT INTO MARC (SEQ, MARC_DATA, DELETE_YN) VALUES (?,?,'N')", current["SEQ"], marc)
        execute(conn, "UPDATE BOOK_LENT SET STATS=? WHERE SEQ=?", state, current["SEQ"])
    else:
        seq = next_seq(conn, "BOOK")
        marc = marc_update("", record, {})
        execute(conn, """INSERT INTO BOOK (SEQ, BARCODE, RFID, BOOKNAME, AUTHOR, TOTAL_NAME, CATEGORY, AUTHOR_CODE, CLAIMNUM,
                         COPYNUM, EX_CATE, ISBN, PUBLISH, ATTACH, CLAIM, LOCATION, BOOKIN, BOOKNUM, REG_DATE, MOD_DATE, DELETE_YN)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'','N')""",
                seq, barcode, *columns, stamp())
        execute(conn, "INSERT INTO MARC (SEQ, MARC_DATA, DELETE_YN) VALUES (?,?,'N')", seq, marc)
        execute(conn, """INSERT INTO BOOK_LENT (SEQ, BARCODE, STATS, USERS, LENT_DATE, RETURN_DATE, RESERVE_USER, RESERVE_DATE,
                         EXTEND_COUNT, DELETE_YN) VALUES (?,?,?,'','','','','',0,'N')""", seq, barcode, state)
    if f("uid"):
        if one(conn, "SELECT COUNT(*) AS n FROM BARCODE_UID WHERE BARCODE=?", barcode)["n"]:
            execute(conn, "UPDATE BARCODE_UID SET RFID=? WHERE BARCODE=?", f("uid"), barcode)
        else:
            execute(conn, "INSERT INTO BARCODE_UID (BARCODE, RFID) VALUES (?,?)", barcode, f("uid"))
    return {"ok": True, "book": repo.find_book(conn, barcode, full=True)}


def delete_book(conn, barcode):
    """BookManage.DeleteMarcDB(): refused while the book is out or reserved; otherwise BOOK,
    BOOK_LENT and MARC are marked deleted."""
    barcode = (barcode or "").strip().upper()
    r = one(conn, "SELECT SEQ, STATS, USERS, RESERVE_USER FROM BOOK_LENT WHERE BARCODE=? AND DELETE_YN='N'", barcode)
    if not r:
        return {"error": "해당하는 도서가 없습니다."}
    if r["STATS"] in (1, 3) or (r["USERS"] or "").strip():
        return {"error": "현재 대출중인 도서입니다.\n도서를 반납 후 삭제해주세요."}
    if r["STATS"] == 2 or (r["RESERVE_USER"] or "").strip():
        return {"error": "현재 예약중인 도서입니다.\n예약을 취소 후 삭제해주세요."}
    execute(conn, "UPDATE MARC SET DELETE_YN='Y' WHERE SEQ=?", r["SEQ"])
    execute(conn, "UPDATE BOOK SET DELETE_YN='Y', MOD_DATE=? WHERE SEQ=?", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), r["SEQ"])
    execute(conn, "UPDATE BOOK_LENT SET DELETE_YN='Y' WHERE SEQ=?", r["SEQ"])
    return {"ok": True}
