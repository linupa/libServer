"""Lending, returns and renewals, ported from CLIB's BookLent.LentBook(), BookReturn.ReturnBook()
and ExtendBook(), plus the start-up checks in StartPage (CheckDelayBooks, ReservationBooks,
CheckUsers). The SQL follows CLIB's, with parameters instead of string concatenation.

Every operation returns the shapes the web app expects:
  { "error": msg }                      refused, nothing written
  { "confirm": msg, "title", "ask" }    a 예/아니요 question; call again with answers[ask] = bool
  { "ok": True, ... }                   done and committed

Questions are asked before anything is written, so a refused or unanswered request changes nothing.
"""
from datetime import date, datetime, timedelta

from db import rows

WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]  # Python's weekday() order


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def d10(value):
    return (value or "").strip()[:10]


def parse(day):
    return datetime.strptime(day[:10], "%Y-%m-%d").date()


def one(conn, sql, *params):
    found = rows(conn, sql, *params)
    return found[0] if found else None


def execute(conn, sql, *params):
    cur = conn.cursor()
    cur.execute(sql, params)
    cur.close()


def next_seq(conn, table):
    """CLIB numbers history rows with MAX(SEQ)+1; lock the table so two requests can't collide."""
    r = one(conn, f"SELECT MAX(SEQ) AS m FROM {table} WITH (UPDLOCK, HOLDLOCK)")
    return (r["m"] or 0) + 1


def option(conn):
    return one(conn, "SELECT * FROM LENT_OPTION") or {}


def has_attach(text):
    # BOOK.ATTACH holds the attachment's description; 'N' or empty means none
    text = (text or "").strip()
    return text and text != "N"


# ---- book and member lookups ---------------------------------------------

BOOK = """
SELECT B.BARCODE, B.BOOKNAME, B.BOOKNUM, B.ATTACH, L.STATS, L.USERS, L.LENT_DATE, L.RETURN_DATE, L.EXTEND_COUNT,
       L.RESERVE_USER, L.ATTACH AS BATTACH, L.ATTACH_USER,
       (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='001' AND SUB_CODE=L.STATS) AS STAT,
       (SELECT USER_NAME FROM USERS WHERE USER_CODE=L.RESERVE_USER AND DELETE_YN='N') AS RESERVE_NAME
FROM BOOK AS B JOIN BOOK_LENT AS L ON L.SEQ = B.SEQ
WHERE B.DELETE_YN = 'N' AND L.DELETE_YN = 'N' AND B.BARCODE = ?
"""


def find_book(conn, code):
    """SelectBookQuery, then CLIB's fallback for short barcodes: keep the letters and pad the
    number with zeros to each barcode length in use (HK915 -> HK00000915)."""
    code = (code or "").strip().upper()
    found = one(conn, BOOK, code)
    if found or not code:
        return found
    digits = next((i for i, ch in enumerate(code) if ch.isdigit()), len(code))
    prefix, number = code[:digits], code[digits:]
    if not number.isdigit():
        return None
    number = str(int(number))
    lengths = [r["n"] for r in rows(conn, "SELECT DISTINCT LEN(BARCODE) AS n FROM BOOK WHERE BARCODE LIKE ? ORDER BY n",
                                    prefix + "%")]
    for n in lengths:
        width = n - len(prefix)
        if width >= len(number):
            found = one(conn, BOOK, prefix + number.zfill(width))
            if found:
                return found
    return None


USER = """
SELECT USER_CODE, USER_NAME, USER_STATE, DISABLE_DATE, DELAY_CHARGE,
       (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='003' AND SUB_CODE=A.USER_STATE) AS USTATE,
       (SELECT RENTAL_DATE FROM USER_LEVEL WHERE CODE_NUMBER=A.USER_LEVEL) AS RENTAL_DATE,
       (SELECT RENTAL_MAX FROM USER_LEVEL WHERE CODE_NUMBER=A.USER_LEVEL) AS RENTAL_MAX,
       (SELECT COUNT(*) FROM BOOK_LENT WHERE DELETE_YN='N' AND USERS=A.USER_CODE) AS RENTAL_COUNT
FROM USERS AS A WHERE DELETE_YN = 'N' AND USER_CODE = ?
"""


def find_user(conn, user_id):
    return one(conn, USER, (user_id or "").strip().upper())


def title_of(book):
    """서명.권차, as the kiosk (CLIB_Self) shows it."""
    title, volume = (book["BOOKNAME"] or "").strip(), (book["BOOKNUM"] or "").strip()
    return f"{title}.{volume}" if volume else title


# ---- due dates -------------------------------------------------------------

def open_day(conn, day):
    """Move past closed days: REST_WEEK weekdays, REST_DATE dates and PUBLIC_RESTDATE holidays."""
    week = one(conn, "SELECT * FROM REST_WEEK") or {}
    for _ in range(366):
        text = day.isoformat()
        if week.get(WEEKDAYS[day.weekday()]):
            day += timedelta(days=1)
        elif one(conn, "SELECT RESTDATE FROM REST_DATE WHERE RESTDATE = ?", text):
            day += timedelta(days=1)
        elif one(conn, "SELECT DATE FROM PUBLIC_RESTDATE WHERE REST = 1 AND DATE = ?", text[5:]):
            day += timedelta(days=1)
        else:
            return day
    return day


def loan_days(conn, user_id):
    """The member's grade's loan days, one fewer when 대출일 포함하기 (LENTDATE) is on."""
    r = one(conn, """SELECT RENTAL_DATE FROM USER_LEVEL WHERE CODE_NUMBER =
                     (SELECT USER_LEVEL FROM USERS WHERE USER_CODE = ? AND DELETE_YN = 'N')""", user_id)
    days = r["RENTAL_DATE"] if r else 0
    if option(conn).get("LENTDATE") and days > 0:
        days -= 1
    return days


# ---- start-up checks (StartPage) ---------------------------------------------

def daily_checks(conn):
    """CheckDelayBooks, ReservationBooks and CheckUsers, which CLIB runs when it starts."""
    today = date.today().isoformat()
    stamp = now()
    # CheckDelayBooks: loans past their due date become 연체중, and so does the member;
    # the first time, a 연체 row (BOOK_STATE 3) goes into the history
    late = rows(conn, """SELECT BARCODE, USERS, STATS FROM BOOK_LENT
                         WHERE RETURN_DATE != '' AND SUBSTRING(RETURN_DATE, 1, 10) < ? AND DELETE_YN = 'N'""", today)
    for r in late:
        execute(conn, "UPDATE BOOK_LENT SET STATS=3 WHERE BARCODE=? AND DELETE_YN='N'", r["BARCODE"])
        execute(conn, "UPDATE USERS SET USER_STATE=1 WHERE DELETE_YN='N' AND USER_CODE=?", r["USERS"])
        if r["STATS"] != 3:
            execute(conn, "INSERT INTO RENTAL_HISTORY (SEQ,BOOK_CODE,BOOK_STATE,USER_CODE,REG_DATE) VALUES (?,?,3,?,?)",
                    next_seq(conn, "RENTAL_HISTORY"), r["BARCODE"], r["USERS"], stamp)
    # ReservationBooks: a book held longer than RESERVE_DAY goes to the next member waiting
    hold = option(conn).get("RESERVE_DAY") or 3
    for r in rows(conn, "SELECT BARCODE, RESERVE_USER, RESERVE_DATE FROM BOOK_LENT WHERE DELETE_YN='N' AND RESERVE_DATE != '' AND RESERVE_DATE < ?", today):
        if (date.today() - parse(r["RESERVE_DATE"])).days > hold:
            execute(conn, "DELETE FROM RESERVATION WHERE BOOK_CODE=? AND USER_CODE=?", r["BARCODE"], r["RESERVE_USER"])
            nxt = one(conn, "SELECT USER_CODE FROM RESERVATION WHERE BOOK_CODE=? ORDER BY REG_DATE", r["BARCODE"])
            if nxt:
                execute(conn, "UPDATE BOOK_LENT SET STATS=2, RESERVE_USER=?, RESERVE_DATE=? WHERE BARCODE=? AND DELETE_YN='N'",
                        nxt["USER_CODE"], today, r["BARCODE"])
            else:
                execute(conn, "UPDATE BOOK_LENT SET STATS=0, RESERVE_USER='', RESERVE_DATE='' WHERE BARCODE=? AND DELETE_YN='N'",
                        r["BARCODE"])
    # CheckUsers: suspensions that have run out end
    execute(conn, """UPDATE USERS SET USER_STATE=0, DISABLE_DATE='' WHERE DELETE_YN='N' AND DISABLE_DATE != ''
                     AND SUBSTRING(DISABLE_DATE, 1, 10) < ?""", today)
    return {"overdue": len(late)}


# ---- lend (BookLent.LentBook) ------------------------------------------------

def lend(conn, user_id, barcode, answers):
    o = option(conn)
    book = find_book(conn, barcode)
    if not book:
        return {"error": "해당하는 도서가 없습니다."}
    code = book["BARCODE"]
    user_id = (user_id or "").strip().upper()
    if book["STATS"] not in (0, 2):
        return {"error": f"{(book['STAT'] or '').strip()} 도서입니다."}
    reserver = (book["RESERVE_USER"] or "").strip()
    if reserver and reserver != user_id:
        return {"error": f"예약중인 도서입니다.\n예약회원 : {reserver}\n이름 : {(book['RESERVE_NAME'] or '').strip()}"}

    # 반납 후 바로 대출 금지: the ban runs RELENT_DAY days from the last return, counting that day.
    # (CLIB compares these dates the wrong way round; this follows its message.)
    if o.get("RELENT_ENABLE") and (o.get("RELENT_DAY") or 0) > 0:
        last = one(conn, """SELECT TOP 1 SUBSTRING(REG_DATE,1,10) AS d FROM RENTAL_HISTORY
                            WHERE BOOK_STATE=0 AND BOOK_CODE=? AND USER_CODE=? ORDER BY REG_DATE DESC""", code, user_id)
        if last and last["d"]:
            until = (parse(last["d"]) + timedelta(days=o["RELENT_DAY"] - 1)).isoformat()
            if date.today().isoformat() <= until:
                return {"error": f"동일 도서 대출 금지기간입니다.\n{until} 까지"}

    user = find_user(conn, user_id)
    if not user:
        return {"error": "해당하는 회원이 없습니다."}
    if user["RENTAL_COUNT"] >= (user["RENTAL_MAX"] or 0):
        return {"error": "최대 대출권수만큼 대출중인 회원입니다."}
    state = (user["USTATE"] or "").strip()
    if user["USER_STATE"] == 2 or (user["USER_STATE"] == 1 and not o.get("DELAY_LENT")):
        return {"error": f"{state} 회원입니다."}

    # 재대출 관리: ask when the member has borrowed this book before. CLIB counts every history
    # row, so a member collecting a book they reserved was asked too; count only loans (1).
    if o.get("RE_LENT") and "relend" not in answers and one(conn,
            "SELECT COUNT(*) AS n FROM RENTAL_HISTORY WHERE USER_CODE=? AND BOOK_CODE=? AND BOOK_STATE=1", user_id, code)["n"] > 0:
        return {"confirm": "해당 회원이 대출했던 도서입니다.\n다시 대출하시겠습니까?", "title": "도서대출", "ask": "relend"}
    if answers.get("relend") is False:
        return {"cancelled": True}

    # 딸림자료 대출관리
    lend_attach = False
    attach_out = (book["BATTACH"] or "").strip()
    if o.get("ATTACH") and has_attach(book["ATTACH"]):
        if attach_out in ("N", ""):
            if "attach" not in answers:
                return {"confirm": f"딸림자료 : {book['ATTACH'].strip()}\n딸림자료가 있는 도서입니다.\n함께 대출하시겠습니까?",
                        "title": "딸림자료대출", "ask": "attach"}
            lend_attach = bool(answers["attach"])
        elif attach_out == "Y":
            if "attachOut" not in answers:
                return {"confirm": "아직 딸림자료가 반납되지 않았습니다.\n대출을 진행하시겠습니까?",
                        "title": "딸림자료 대출", "ask": "attachOut"}
            if not answers["attachOut"]:
                return {"cancelled": True}

    # 독서통장: CLIB also writes BANKBOOK_HISTORY for members with a bankbook; not ported yet
    if one(conn, "SELECT USE_YN FROM BANKBOOK_OPTION WHERE USE_YN='Y'") and \
            one(conn, "SELECT COUNT(*) AS n FROM BANKBOOK_USER WHERE USERCODE=?", user_id)["n"]:
        return {"error": "독서통장 회원의 대출은 아직 웹에서 처리할 수 없습니다.\nCLIB에서 대출해주세요."}

    # Write: everything below happens in one transaction
    stamp = now()
    due = open_day(conn, date.today() + timedelta(days=loan_days(conn, user_id))).isoformat()
    # answers.preview: every check passed; report what would happen without writing (the
    # kiosk shows it in its "대출하시겠습니까?" dialog, then asks again without preview)
    if answers.get("preview"):
        return {"preview": {"userId": user_id, "userName": (user["USER_NAME"] or "").strip(), "barcode": code,
                            "title": title_of(book), "lentDate": stamp[:10], "dueDate": due}}
    if lend_attach:
        execute(conn, "UPDATE BOOK_LENT SET ATTACH='Y', ATTACH_USER=? WHERE BARCODE=? AND DELETE_YN='N'", user_id, code)
        execute(conn, "INSERT INTO ATTACH_HISTORY (SEQ,BOOK_CODE,STATE,USER_CODE,REG_DATE) VALUES (?,?,0,?,?)",
                next_seq(conn, "ATTACH_HISTORY"), code, user_id, date.today().isoformat())
    if reserver:
        execute(conn, "DELETE FROM RESERVATION WHERE BOOK_CODE=? AND USER_CODE=?", code, user_id)
    nxt = one(conn, "SELECT USER_CODE FROM RESERVATION WHERE BOOK_CODE=? ORDER BY REG_DATE", code)
    execute(conn, """UPDATE BOOK_LENT SET STATS=1, USERS=?, RESERVE_USER=?, RESERVE_DATE='', LENT_DATE=?,
                     RETURN_DATE=?, EXTEND_COUNT=0 WHERE BARCODE=? AND DELETE_YN='N'""",
            user_id, nxt["USER_CODE"] if nxt else "", stamp, due, code)
    execute(conn, "INSERT INTO RENTAL_HISTORY (SEQ,BOOK_CODE,BOOK_STATE,USER_CODE,REG_DATE) VALUES (?,?,1,?,?)",
            next_seq(conn, "RENTAL_HISTORY"), code, user_id, stamp)
    return {"ok": True, "loan": {"barcode": code, "userId": user_id, "lentDate": stamp[:10], "dueDate": due,
                                 "withAttach": lend_attach}}


# ---- return (BookReturn.ReturnBook) ------------------------------------------

def return_book(conn, barcode, answers):
    o = option(conn)
    book = find_book(conn, barcode)
    if not book:
        return {"error": "해당하는 도서가 없습니다."}
    code = book["BARCODE"]
    user_id = (book["USERS"] or "").strip()
    if book["STATS"] not in (1, 3) and not user_id:
        return {"error": "대출중인 도서가 아닙니다."}
    reserver = (book["RESERVE_USER"] or "").strip()
    # The kiosk (CLIB_Self) leaves books someone is waiting for to the desk
    if answers.get("kiosk") and reserver:
        return {"error": "예약된 도서입니다.\n데스크에 직접 반납해주시기 바랍니다."}

    # Ask everything first: the borrower missing, and whether the 딸림자료 comes back too
    user = find_user(conn, user_id) if user_id else None
    if not user and "missingUser" not in answers:
        return {"confirm": "대출한 회원의 정보가 조회되지 않습니다.\n반납처리를 계속하시겠습니까?",
                "title": "회원정보 오류", "ask": "missingUser"}
    if not user and answers.get("missingUser") is False:
        return {"cancelled": True}
    attach_back = False
    if o.get("ATTACH") and (book["BATTACH"] or "").strip() == "Y" and (book["ATTACH_USER"] or "").strip() == user_id:
        if "attach" not in answers:
            return {"confirm": "딸림자료가 함께 대출되었습니다.\n딸림자료도 반납하시겠습니까?", "title": "딸림자료 반납", "ask": "attach"}
        attach_back = bool(answers["attach"])
    if answers.get("preview"):
        return {"preview": {"userId": user_id, "userName": (user["USER_NAME"] or "").strip() if user else "",
                            "barcode": code, "title": title_of(book), "lentDate": d10(book["LENT_DATE"]),
                            "dueDate": d10(book["RETURN_DATE"])}}

    messages = []
    today = date.today()
    due = d10(book["RETURN_DATE"])
    if due and parse(due) < today and user:
        # CLIB counts one day fewer for suspensions and adds it back for fines
        delay = (today - parse(due)).days - 1
        suspended_to = today + timedelta(days=delay)
        state, disable, charge = 0, "", 0
        mode = o.get("DELAY") or 0
        if mode == 1:  # 대출정지부여
            current = d10(user["DISABLE_DATE"])
            until = suspended_to if not current else parse(current)
            if current:
                if (o.get("DELAYDATE") or 0) == 0:  # 가장 큰 연체일 기준
                    until = max(until, suspended_to)
                else:  # 연체일 누적
                    until = until + timedelta(days=delay)
            disable, state = until.isoformat(), 2
            messages.append(f"연체된 도서입니다.\n해당 회원은 다음 기간까지 대출정지됩니다.\n대출정지기간 : {disable}까지")
        elif mode == 2:  # 연체금납부
            delay += 1
            fee = delay * (o.get("DELAY_CHARGE") or 0)
            charge = min((user["DELAY_CHARGE"] or 0) + fee, o.get("DELAY_MAX") or 0)
            if o.get("DISABLE_CHK"):
                state = 2
                messages.append(f"연체된 도서입니다.\n연체금 납부시까지 대출정지됩니다.\n연체금 : {fee} 원\n 총 연체금액 : {charge} 원")
            else:
                messages.append(f"연체된 도서입니다.\n연체금 : {fee} 원\n 총 연체금액 : {charge} 원")
        else:  # 적용안함: still 연체중 while other books are overdue
            others = one(conn, """SELECT COUNT(*) AS n FROM BOOK_LENT WHERE DELETE_YN='N' AND USERS=? AND STATS=3
                                  AND BARCODE != ?""", user_id, code)["n"]
            state = 1 if others else 0
        # CLIB then marks the member 연체중 whenever other overdue books remain, even over a suspension
        if one(conn, "SELECT COUNT(*) AS n FROM BOOK_LENT WHERE DELETE_YN='N' AND STATS=3 AND USERS=?", user_id)["n"] - 1 > 0:
            state = 1
        execute(conn, "UPDATE USERS SET USER_STATE=?, DISABLE_DATE=?, DELAY_CHARGE=? WHERE USER_CODE=? AND DELETE_YN='N'",
                state, disable, charge, user_id)

    if reserver:
        execute(conn, """UPDATE BOOK_LENT SET STATS=2, USERS='', LENT_DATE='', RETURN_DATE='', RESERVE_DATE=?,
                         EXTEND_COUNT=0 WHERE BARCODE=?""", today.isoformat(), code)
    else:
        execute(conn, "UPDATE BOOK_LENT SET STATS=0, USERS='', LENT_DATE='', RETURN_DATE='', EXTEND_COUNT=0 WHERE BARCODE=?", code)
    execute(conn, "INSERT INTO RENTAL_HISTORY (SEQ,BOOK_CODE,BOOK_STATE,USER_CODE,REG_DATE) VALUES (?,?,0,?,?)",
            next_seq(conn, "RENTAL_HISTORY"), code, user_id, now())
    if attach_back:
        execute(conn, "UPDATE BOOK_LENT SET ATTACH='N', ATTACH_USER='' WHERE DELETE_YN='N' AND BARCODE=?", code)
        execute(conn, "INSERT INTO ATTACH_HISTORY (SEQ,BOOK_CODE,STATE,USER_CODE,REG_DATE) VALUES (?,?,1,?,?)",
                next_seq(conn, "ATTACH_HISTORY"), code, user_id, today.isoformat())
    if reserver:
        messages.append(f"예약된 회원이 있습니다.\n예약회원 : {reserver}\n이름 : {(book['RESERVE_NAME'] or '').strip()}")
    return {"ok": True, "userId": user_id, "barcode": code, "messages": messages}


# ---- renew (ExtendBook) ----------------------------------------------------------

def extend(conn, barcode):
    o = option(conn)
    if not o.get("EXTEND"):
        return {"error": "[연장불가] 상태입니다.\n연장을 허용하시려면 [대출환경설정]에서\n[연장관리] 옵션을 설정해주세요."}
    book = find_book(conn, barcode)
    if not book:
        return {"error": "해당하는 도서가 없습니다."}
    code = book["BARCODE"]
    reserver = (book["RESERVE_USER"] or "").strip()
    if reserver:
        return {"error": f"예약중인 도서입니다.\n예약회원 : {reserver}\n이름 : {(book['RESERVE_NAME'] or '').strip()}"}
    if book["STATS"] == 3:
        return {"error": "연체중인 도서입니다."}
    if book["STATS"] != 1:
        return {"error": "대출중인 도서가 아닙니다."}
    count = book["EXTEND_COUNT"] or 0
    if count >= (o.get("EXTEND_MAX") or 0):
        return {"error": "최대 연장횟수만큼 연장된 도서입니다."}
    user_id = (book["USERS"] or "").strip()
    # 대출일 비례: the grade's loan days x EXTEND_DAY; 일괄적용: EXTEND_DAY days
    days = loan_days(conn, user_id) * o["EXTEND_DAY"] if o["EXTEND"] == 1 else o["EXTEND_DAY"]
    due = open_day(conn, parse(book["RETURN_DATE"]) + timedelta(days=days)).isoformat()
    execute(conn, "UPDATE BOOK_LENT SET RETURN_DATE=?, EXTEND_COUNT=? WHERE USERS=? AND BARCODE=? AND DELETE_YN='N'",
            due, count + 1, user_id, code)
    return {"ok": True, "loan": {"barcode": code, "userId": user_id, "dueDate": due, "extended": count + 1},
            "message": f"연장되었습니다.\n반납예정일 : {due}"}


# ---- reserve (BookReserve.ReserveBook) ----------------------------------------

def reserve(conn, user_id, barcode):
    o = option(conn)
    if not o.get("RESERVE"):
        return {"error": "[예약불가] 상태입니다.\n예약을 사용하시려면 [대출반납설정]에서\n[예약관리]를 설정해주세요"}
    book = find_book(conn, barcode)
    if not book:
        return {"error": "해당하는 도서가 없습니다."}
    code = book["BARCODE"]
    user_id = (user_id or "").strip().upper()
    # Only books that are out (대출중 1, 예약중 2, 연체중 3) can be reserved
    if book["STATS"] == 0 or book["STATS"] > 3:
        return {"error": "대출중, 연체중, 예약중인 도서만 예약 할 수 있습니다."}
    waiting = one(conn, "SELECT COUNT(*) AS n FROM RESERVATION WHERE BOOK_CODE=?", code)["n"]
    limit = o.get("RESERVE_MAX") or 0
    if limit <= waiting:
        return {"error": f"예약 대기자가 최대인 도서입니다.\n최대 대기자수 : {limit} 명\n현재 대기자수 : {waiting} 명"}
    if (book["USERS"] or "").strip() == user_id:
        return {"error": "해당 도서 대출자입니다."}
    user = one(conn, """SELECT USER_CODE, USER_STATE,
                        (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='003' AND SUB_CODE=A.USER_STATE) AS USTATE,
                        (SELECT RESERVE_MAX FROM USER_LEVEL WHERE CODE_NUMBER=A.USER_LEVEL) AS RESERVE_MAX,
                        (SELECT COUNT(*) FROM RESERVATION WHERE USER_CODE=A.USER_CODE) AS RESERVE_COUNT
                        FROM USERS AS A WHERE DELETE_YN='N' AND USER_CODE=?""", user_id)
    if not user:
        return {"error": "해당하는 회원이 없습니다."}
    if user["RESERVE_COUNT"] >= (user["RESERVE_MAX"] or 0):
        return {"error": "최대 예약권수만큼 예약중인 회원입니다."}
    if user["USER_STATE"] != 0:
        return {"error": f"{(user['USTATE'] or '').strip()} 회원입니다."}
    if one(conn, "SELECT COUNT(*) AS n FROM RESERVATION WHERE USER_CODE=? AND BOOK_CODE=?", user_id, code)["n"]:
        return {"error": "이미 해당 도서를 예약중인 회원입니다."}

    stamp = now()
    # The first member waiting is kept in BOOK_LENT.RESERVE_USER; a returned book is held for them
    if not (book["RESERVE_USER"] or "").strip():
        execute(conn, "UPDATE BOOK_LENT SET RESERVE_USER=? WHERE BARCODE=?", user_id, code)
    execute(conn, "INSERT INTO RESERVATION (SEQ,BOOK_CODE,USER_CODE,REG_DATE) VALUES (?,?,?,?)",
            next_seq(conn, "RESERVATION"), code, user_id, stamp)
    execute(conn, "INSERT INTO RENTAL_HISTORY (SEQ,BOOK_CODE,BOOK_STATE,USER_CODE,REG_DATE) VALUES (?,?,2,?,?)",
            next_seq(conn, "RENTAL_HISTORY"), code, user_id, stamp)
    return {"ok": True, "barcode": code, "userId": user_id, "position": waiting + 1}


def cancel_reserve(conn, user_id, barcode):
    book = find_book(conn, barcode)
    if not book:
        return {"error": "해당하는 도서가 없습니다."}
    code = book["BARCODE"]
    user_id = (user_id or "").strip().upper()
    if not find_user(conn, user_id):
        return {"error": "해당하는 회원이 없습니다."}
    if not one(conn, "SELECT COUNT(*) AS n FROM RESERVATION WHERE USER_CODE=? AND BOOK_CODE=?", user_id, code)["n"]:
        return {"error": "해당 도서를 예약중인 회원이 아닙니다."}
    execute(conn, "DELETE FROM RESERVATION WHERE USER_CODE=? AND BOOK_CODE=?", user_id, code)
    nxt = one(conn, "SELECT USER_CODE FROM RESERVATION WHERE BOOK_CODE=? ORDER BY REG_DATE", code)
    if nxt:
        execute(conn, "UPDATE BOOK_LENT SET RESERVE_USER=? WHERE BARCODE=?", nxt["USER_CODE"], code)
    elif book["STATS"] == 2:
        # Nobody else waiting for a held book: it is free again. (CLIB leaves RESERVE_DATE set.)
        execute(conn, "UPDATE BOOK_LENT SET STATS=0, RESERVE_USER='', RESERVE_DATE='' WHERE BARCODE=?", code)
    else:
        execute(conn, "UPDATE BOOK_LENT SET RESERVE_USER='' WHERE BARCODE=?", code)
    return {"ok": True, "message": "예약이 취소되었습니다"}
