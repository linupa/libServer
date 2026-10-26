"""Read queries against CLIB's tables, returning the same shapes as the web app's
sample library (web/js/data.js), so screens work the same against either.

Codes are resolved through CODE_SUB: 000 회원등급, 001 도서상태, 002 소장위치, 003 회원상태, 004 반입구분.
BOOK_LENT.STATS 1 = 대출중, 3 = 연체중. RENTAL_HISTORY.BOOK_STATE 1 = 대출, 0 = 반납, 3 = 연체.
"""
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from db import config, rows

LENT = (1, 3)
HISTORY_KIND = {1: "대출", 0: "반납", 3: "연체", 2: "예약"}


def today():
    return date.today().isoformat()


def d10(value):
    """CLIB stores dates as text ('2026-08-02 12:21:31', sometimes '2017-05-07, 13:16:36')."""
    return (value or "").strip()[:10]


def codes(conn):
    out = {}
    for r in rows(conn, "SELECT CODE_NUMBER, SUB_CODE, SUB_NAME FROM CODE_SUB ORDER BY CODE_NUMBER, SUB_CODE"):
        out.setdefault(r["CODE_NUMBER"], {})[r["SUB_CODE"]] = r["SUB_NAME"].strip()
    return out


def clib_config():
    """The few CLIB.exe.Config keys the web app needs. DBCONN (with its password) is skipped."""
    wanted = {"AUTHORCODE", "AUTHOR", "BOOK", "MOUM", "TOTAL", "PUBLISH", "ISBN_SEARCH", "USERCODE",
              "CARD_LEFTMARGIN", "CARD_TOPMARGIN", "CARD_OUTLINE",
              "CLAIM_LABEL", "CLAIM_OUTLINE", "CLAIM_ALIGN", "CLAIM_BARCODE", "CLAIM_LEFTMARGIN", "CLAIM_TOPMARGIN",
              "CLAIM_LOCATION", "CLAIM_FONT", "CLAIM_FONTSIZE", "CLAIM_V", "CLAIM_C", "CLAIM_VUPPER", "CLAIM_CUPPER"}
    path = Path(config()["clibDir"]) / "CLIB.exe.Config"
    out = {}
    if path.exists():
        for add in ET.parse(path).getroot().iter("add"):
            if add.get("key") in wanted:
                out[add.get("key")] = add.get("value")
    # Values saved from the web (settings_store.py) take precedence
    import settings_store
    out.update({k: v for k, v in settings_store.overlay().items() if k in wanted})
    return out


def settings(conn):
    c = codes(conn)
    cfg = clib_config()
    num = lambda k, d=0: int(cfg.get(k, d) or d)
    grades = [{"code": g["CODE_NUMBER"], "name": c.get("000", {}).get(g["CODE_NUMBER"], str(g["CODE_NUMBER"])),
               "prefix": (g["CLASSIFY"] or "").strip(), "lendDays": g["RENTAL_DATE"], "maxLend": g["RENTAL_MAX"],
               "maxReserve": g["RESERVE_MAX"]}
              for g in rows(conn, "SELECT * FROM USER_LEVEL ORDER BY CODE_NUMBER")]
    o = (rows(conn, "SELECT * FROM LENT_OPTION") or [{}])[0]
    lib = (rows(conn, "SELECT NAME, PHONE, ADDRESS, EMAIL, NOTICE FROM LIBRARY") or [{}])[0]
    week = (rows(conn, "SELECT * FROM REST_WEEK") or [{}])[0]
    days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    # LIBRARY.NOTICE holds the card back: title, notice and library name separated by tabs
    notice = (lib.get("NOTICE") or "").split("\t")
    bank = (rows(conn, "SELECT * FROM BANKBOOK_OPTION") or [{}])[0]
    return {
        "library": {"name": lib.get("NAME") or "", "phone": lib.get("PHONE") or "",
                    "address": lib.get("ADDRESS") or "", "email": lib.get("EMAIL") or ""},
        "card": {"title": notice[0] if notice[0] else "이  용  안  내", "notice": notice[1] if len(notice) > 1 else "",
                 "libraryName": notice[2] if len(notice) > 2 and notice[2] else (lib.get("NAME") or ""),
                 "leftMargin": num("CARD_LEFTMARGIN", 20), "topMargin": num("CARD_TOPMARGIN", 35),
                 "outline": cfg.get("CARD_OUTLINE") == "1"},
        # 청구기호 출력 (ClaimPrint): CLIB.exe.Config CLAIM_*. The v./c. options default to on,
        # as their check boxes are ticked in CLIB's designer until first changed.
        "claim": {"label": num("CLAIM_LABEL"), "outline": cfg.get("CLAIM_OUTLINE", "0") == "0",
                  "align": "center" if cfg.get("CLAIM_ALIGN") == "1" else "left", "barcode": cfg.get("CLAIM_BARCODE") == "1",
                  "leftMargin": num("CLAIM_LEFTMARGIN"), "topMargin": num("CLAIM_TOPMARGIN"), "skip": num("CLAIM_LOCATION"),
                  "font": num("CLAIM_FONT"), "fontSize": num("CLAIM_FONTSIZE", 10),
                  **{k: cfg.get(f"CLAIM_{key}", "1") == "1" for k, key in
                     (("v", "V"), ("c", "C"), ("vUpper", "VUPPER"), ("cUpper", "CUPPER"))}},
        "bankbook": {"enabled": str(bank.get("USE_YN") or "").upper() in ("Y", "1"), "port": bank.get("PORT") or "",
                     "library": bank.get("LIBRARY") or "", "address": bank.get("L_ADDRESS") or "",
                     "phone": bank.get("PHONE") or "", "homepage": bank.get("HOMEPAGE") or "",
                     "time1": bank.get("TIME1") or "", "time2": bank.get("TIME2") or "", "time3": bank.get("TIME3") or "",
                     "greeting": str(bank.get("FIRSTPRINT") or "").upper() in ("Y", "1"), "greetingText": bank.get("FIRSTMSG") or ""},
        # UserOption: USERCODE "0" = 회원등급별로 회원번호 사용
        "userCodeByGrade": cfg.get("USERCODE", "1") == "0",
        # BookOption radios: AUTHOR/BOOK 0 = 음절, 1 = 초성; MOUM 1 = 기호표시; TOTAL 0 = 총서명 사용; PUBLISH 0 = 출판사명 표시
        "book": {"authorCode": {"table": num("AUTHORCODE", 5), "authorInitial": cfg.get("AUTHOR") == "1",
                                "titleInitial": cfg.get("BOOK", "1") == "1", "moum": cfg.get("MOUM", "1") == "1"},
                 "useSeriesTitle": cfg.get("TOTAL", "0") == "0", "showPublisher": cfg.get("PUBLISH") == "0",
                 "isbnSearch": num("ISBN_SEARCH")},
        "lend": {
            "includeLentDay": bool(o.get("LENTDATE")), "attach": bool(o.get("ATTACH")),
            "relentConfirm": bool(o.get("RE_LENT")), "relentBan": bool(o.get("RELENT_ENABLE")),
            "relentDays": o.get("RELENT_DAY") or 1, "delay": o.get("DELAY") or 0, "delayBasis": o.get("DELAYDATE") or 0,
            "delayCharge": o.get("DELAY_CHARGE") or 0, "delayChargeMax": o.get("DELAY_MAX") or 0,
            "delayLent": bool(o.get("DELAY_LENT")), "chargeSuspend": bool(o.get("DISABLE_CHK")),
            "extend": o.get("EXTEND") or 0, "extendDays": o.get("EXTEND_DAY") or 0, "extendMax": o.get("EXTEND_MAX") or 0,
            "reserve": o.get("RESERVE") or 0, "reserveDays": o.get("RESERVE_DAY") or 0, "reserveMax": o.get("RESERVE_MAX") or 0,
            "closedWeekdays": [i for i, d in enumerate(days) if week.get(d)], "closedDates": [],
        },
        "grades": grades,
        "locations": [{"code": k, "name": v} for k, v in c.get("002", {}).items()],
        "exCategories": ex_categories(conn),
        "codes": {"state": list(c.get("001", {}).values()), "userState": list(c.get("003", {}).values()),
                  "bookIn": list(c.get("004", {}).values())},
    }


# ---- MARC -----------------------------------------------------------------

FT, SF, RT = "\x1e", "\x1f", "\x1d"  # field terminator, subfield delimiter, record terminator


def marc_fields(data):
    """ISO 2709: 24-char leader, 12-char directory entries (tag, length, start), then the fields.
    CLIB's lengths count CP949 bytes, so take the fields in directory order by splitting on
    the field terminator instead of slicing by position."""
    if not data or len(data) < 24:
        return []
    head, _, body = data.partition(FT)
    tags = [head[i:i + 3] for i in range(24, len(head) - 11, 12)]
    return list(zip(tags, body.rstrip(RT).split(FT)))


def subfield(body, code):
    for part in body.split(SF)[1:]:
        if part[:1] == code:
            return part[1:].strip()
    return ""


def marc_view(data):
    """The fields BookManage shows that only live in MARC (AnalysisMarc.MarcAnalysis),
    and the record as CLIB's 전문가용 tab writes it (▼ subfield, ▲ field end, ↔ record end)."""
    fields = marc_fields(data)
    get = lambda tag, code: next((subfield(b, code) for t, b in fields if t == tag), "")
    lines = [data[:24] + "▲"] if data else []
    for tag, body in fields:
        if tag < "010":
            lines.append(f"{tag}\t\t{body}▲")
        else:
            lines.append(f"{tag}\t{body[:2]}\t{body[2:].replace(SF, '▼')}▲")
    publisher = get("260", "b")
    return {
        "pubPlace": get("260", "a").rstrip(" :"), "year": get("260", "c").rstrip(" ."),
        "publisher": publisher.rstrip(" ,"), "pages": get("300", "a").rstrip(" :;"),
        "size": get("300", "c").rstrip(" +"), "attachText": get("300", "e"),
        "price": get("950", "b").lstrip("\\").strip(), "marcText": "\n".join(lines) + ("↔" if lines else ""),
    }


# ---- books --------------------------------------------------------------

BOOK_SQL = """
SELECT B.SEQ, B.BARCODE, B.BOOKNAME, B.BOOKNUM, B.AUTHOR, B.TOTAL_NAME, B.CATEGORY, B.AUTHOR_CODE, B.CLAIMNUM,
       B.COPYNUM, B.EX_CATE, B.ISBN, B.PUBLISH, B.ATTACH, B.RFID, B.REG_DATE, B.MOD_DATE,
       (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='002' AND SUB_CODE=B.LOCATION) AS LOCATION_NAME,
       (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='004' AND SUB_CODE=B.BOOKIN) AS BOOKIN_NAME,
       (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='001' AND SUB_CODE=L.STATS) AS STATE_NAME,
       L.STATS, L.USERS, L.LENT_DATE, L.RETURN_DATE, L.EXTEND_COUNT, L.RESERVE_USER, L.RESERVE_DATE,
       L.ATTACH AS ATTACH_OUT, L.ATTACH_USER,
       U.USER_NAME, U.PHONE_NUMBER, U.ADDRESS
FROM BOOK AS B JOIN BOOK_LENT AS L ON L.SEQ = B.SEQ
LEFT JOIN USERS AS U ON U.USER_CODE = L.USERS AND U.DELETE_YN = 'N'
WHERE B.DELETE_YN = 'N' AND L.DELETE_YN = 'N'
"""


def claim(r):
    parts = [(r["EX_CATE"] or "").strip(), f"{(r['CATEGORY'] or '').strip()}-{(r['AUTHOR_CODE'] or '').strip()}",
             (r["CLAIMNUM"] or "").strip() and f"v.{r['CLAIMNUM'].strip()}",
             (r["COPYNUM"] or "").strip() and f"c.{r['COPYNUM'].strip()}"]
    return " ".join(p for p in parts if p)


def book_view(r, queue=()):
    lent = r["STATS"] in LENT
    overdue = lent and (r["STATS"] == 3 or d10(r["RETURN_DATE"]) < today())
    state = "연체중" if overdue else (r["STATE_NAME"] or "").strip()
    loan = None
    if lent:
        loan = {"barcode": r["BARCODE"], "userId": r["USERS"], "userName": r["USER_NAME"] or "",
                "lentDate": d10(r["LENT_DATE"]), "dueDate": d10(r["RETURN_DATE"]), "extended": r["EXTEND_COUNT"] or 0,
                "withAttach": (r["ATTACH_OUT"] or "") == "Y", "state": "연체중" if overdue else "대출중",
                "user": {"userId": r["USERS"], "userName": r["USER_NAME"] or "", "phone": r["PHONE_NUMBER"] or "",
                         "address": r["ADDRESS"] or ""}}
    return {
        "barcode": r["BARCODE"], "title": (r["BOOKNAME"] or "").strip(), "volume": (r["BOOKNUM"] or "").strip(),
        "author": (r["AUTHOR"] or "").strip(), "seriesTitle": (r["TOTAL_NAME"] or "").strip(),
        "publisher": (r["PUBLISH"] or "").strip(), "category": (r["CATEGORY"] or "").strip(),
        "authorCode": (r["AUTHOR_CODE"] or "").strip(), "claimVolume": (r["CLAIMNUM"] or "").strip(),
        "copy": (r["COPYNUM"] or "").strip(), "exCate": (r["EX_CATE"] or "").strip(), "isbn": (r["ISBN"] or "").strip(),
        # BOOK.ATTACH is the attachment's description ('N' = none)
        "attach": "" if (r["ATTACH"] or "").strip() == "N" else (r["ATTACH"] or "").strip(), "uid": (r["RFID"] or "").strip(),
        "location": (r["LOCATION_NAME"] or "").strip(), "bookIn": (r["BOOKIN_NAME"] or "").strip(),
        "regDate": d10(r["REG_DATE"]), "modDate": d10(r["MOD_DATE"]),
        "state": state, "claim": claim(r), "queue": list(queue), "loan": loan,
    }


def queues(conn, barcodes=None):
    """Waiting members per book, oldest reservation first."""
    sql = "SELECT BOOK_CODE, USER_CODE FROM RESERVATION"
    params = []
    if barcodes is not None:
        if not barcodes:
            return {}
        sql += f" WHERE BOOK_CODE IN ({','.join('?' * len(barcodes))})"
        params = list(barcodes)
    out = {}
    for r in rows(conn, sql + " ORDER BY REG_DATE, SEQ", *params):
        out.setdefault(r["BOOK_CODE"], []).append(r["USER_CODE"])
    return out


def find_book(conn, barcode, full=False):
    """full=True adds the MARC fields 도서관리 edits (발행지, 출판년도, 페이지, 크기, 가격, …)."""
    found = rows(conn, BOOK_SQL + " AND B.BARCODE = ?", barcode.strip().upper())
    if not found:
        # CLIB's short-barcode fallback (HK915 -> HK00000915)
        import circulation
        match = circulation.find_book(conn, barcode)
        found = rows(conn, BOOK_SQL + " AND B.BARCODE = ?", match["BARCODE"]) if match else []
    if not found:
        return None
    r = found[0]
    book = book_view(r, queues(conn, [r["BARCODE"]]).get(r["BARCODE"], []))
    if full:
        m = rows(conn, "SELECT MARC_DATA FROM MARC WHERE SEQ = ? AND DELETE_YN = 'N'", r["SEQ"])
        add_marc(book, m[0]["MARC_DATA"] if m else "")
    return book


def add_marc(book, marc_data):
    marc = marc_view(marc_data or "")
    # BOOK has the publisher; MARC's 300 ▼e has the attachment's description
    book.update({k: v for k, v in marc.items() if k not in ("publisher", "attachText")})
    if marc["attachText"]:
        book["attach"] = marc["attachText"]
    book["publisher"] = book["publisher"] or marc["publisher"]


def find_books(conn, barcodes, full=False):
    """Many books at once, in the order asked (도서 불러오기 → 도서관리). Same records as
    find_book(), but a handful of set queries instead of three per book."""
    wanted = list(dict.fromkeys(b.strip().upper() for b in barcodes if b and b.strip()))
    found = {}
    for i in range(0, len(wanted), 500):  # SQL Server takes at most 2100 parameters
        chunk = wanted[i:i + 500]
        for r in rows(conn, BOOK_SQL + f" AND B.BARCODE IN ({','.join('?' * len(chunk))})", *chunk):
            found[r["BARCODE"].strip().upper()] = r
    waiting = queues(conn, [r["BARCODE"] for r in found.values()])
    marcs = {}
    if full:
        seqs = [r["SEQ"] for r in found.values()]
        for i in range(0, len(seqs), 500):
            chunk = seqs[i:i + 500]
            for m in rows(conn, f"SELECT SEQ, MARC_DATA FROM MARC WHERE DELETE_YN = 'N' AND SEQ IN ({','.join('?' * len(chunk))})", *chunk):
                marcs.setdefault(m["SEQ"], m["MARC_DATA"])
    out = []
    for barcode in wanted:
        r = found.get(barcode)
        if r is None:
            book = find_book(conn, barcode, full)  # short barcodes (HK915) take the slow path
            if book:
                out.append(book)
            continue
        book = book_view(r, waiting.get(r["BARCODE"], []))
        if full:
            add_marc(book, marcs.get(r["SEQ"], ""))
        out.append(book)
    return out


# ---- self-service kiosk search (CLIB_Self SearchBook) -------------------------

KIOSK_FIELDS = {"서명": "B.BOOKNAME", "저자": "B.AUTHOR", "출판사": "B.PUBLISH", "등록번호": "B.BARCODE",
                "총서명": "B.TOTAL_NAME",
                "전체": "(ISNULL(B.BARCODE,'') + ISNULL(B.BOOKNAME,'') + ISNULL(B.AUTHOR,'') + ISNULL(B.PUBLISH,'')"
                        " + ISNULL(B.CLAIM,'') + ISNULL(B.TOTAL_NAME,''))"}


def kiosk_search(conn, field=None, keyword=""):
    """DBQuery.Search*: books that are on the shelf or out (대출가능, 대출중, 예약중, 연체중,
    대출불가), matched ignoring spaces; no field lists them all (전체도서조회). 발행년도 is the
    year in MARC 008. Only what the kiosk shows: nothing about who has a book."""
    sql = """SELECT B.BARCODE, B.BOOKNAME, B.BOOKNUM, B.AUTHOR, B.PUBLISH, B.CLAIM, L.RETURN_DATE,
                    (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='001' AND SUB_CODE=L.STATS) AS STAT,
                    (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='002' AND SUB_CODE=B.LOCATION) AS LOC,
                    (SELECT MARC_DATA FROM MARC WHERE SEQ=B.SEQ AND DELETE_YN='N') AS MARC_DATA
             FROM BOOK AS B JOIN BOOK_LENT AS L ON L.SEQ = B.SEQ
             WHERE B.DELETE_YN='N' AND L.DELETE_YN='N' AND L.STATS IN (0, 1, 2, 3, 7)"""
    word = (keyword or "").replace(" ", "").upper()
    params = []
    if field in KIOSK_FIELDS:
        sql += f" AND UPPER(REPLACE({KIOSK_FIELDS[field]}, ' ', '')) LIKE ?"
        params.append(f"%{word}%")
    out = []
    for r in rows(conn, sql + " ORDER BY B.BARCODE", *params):
        year = next((body[7:11] for tag, body in marc_fields(r["MARC_DATA"] or "") if tag == "008" and len(body) >= 40), "")
        if field == "발행년도" and year != word:
            continue
        title, volume = (r["BOOKNAME"] or "").strip(), (r["BOOKNUM"] or "").strip()
        out.append({"no": len(out) + 1, "state": (r["STAT"] or "").strip(), "barcode": r["BARCODE"],
                    "title": f"{title}.{volume}" if volume else title, "author": (r["AUTHOR"] or "").strip(),
                    "publisher": (r["PUBLISH"] or "").strip(), "location": (r["LOC"] or "").strip(), "year": year,
                    "claim": (r["CLAIM"] or "").strip(), "dueDate": d10(r["RETURN_DATE"])})
    return out


def ex_categories(conn):
    return [r["EX_CATE"].strip() for r in rows(conn,
            "SELECT DISTINCT EX_CATE FROM BOOK WHERE DELETE_YN='N' AND LEN(LTRIM(RTRIM(EX_CATE))) > 0 ORDER BY EX_CATE")]


SEARCH_FIELDS = {"서명": "B.BOOKNAME", "등록번호": "B.BARCODE", "총서명": "B.TOTAL_NAME", "저자": "B.AUTHOR",
                 "저자기호": "B.AUTHOR_CODE", "ISBN": "B.ISBN", "출판사": "B.PUBLISH", "분류기호": "B.CATEGORY",
                 "별치기호": "B.EX_CATE"}


def search_books(conn, field=None, keyword="", start=None, end=None, limit=1000):
    sql, params = BOOK_SQL, []
    if start is not None or end is not None:
        if start:
            sql += " AND B.BARCODE >= ?"
            params.append(start.strip().upper())
        if end:
            sql += " AND B.BARCODE <= ?"
            params.append(end.strip().upper())
    elif field == "도서상태":
        sql += " AND (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='001' AND SUB_CODE=L.STATS) LIKE ?"
        params.append(f"%{keyword.strip()}%")
    elif field == "소장위치":
        sql += " AND (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='002' AND SUB_CODE=B.LOCATION) LIKE ?"
        params.append(f"%{keyword.strip()}%")
    elif field == "반입구분":
        sql += " AND (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='004' AND SUB_CODE=B.BOOKIN) LIKE ?"
        params.append(f"%{keyword.strip()}%")
    elif field in SEARCH_FIELDS:
        sql += f" AND {SEARCH_FIELDS[field]} LIKE ?"
        params.append(f"%{keyword.strip()}%")
    found = rows(conn, sql.replace("SELECT ", f"SELECT TOP {int(limit)} ", 1) + " ORDER BY B.BARCODE", *params)
    q = queues(conn, [r["BARCODE"] for r in found])
    return [book_view(r, q.get(r["BARCODE"], [])) for r in found]


def all_loans(conn):
    found = rows(conn, BOOK_SQL + " AND L.STATS IN (1, 3) ORDER BY L.LENT_DATE")
    q = queues(conn, [r["BARCODE"] for r in found])
    out = []
    for r in found:
        b = book_view(r, q.get(r["BARCODE"], []))
        out.append({**b["loan"], "book": b})
    return out


def all_reservations(conn):
    q = queues(conn)
    out = []
    for barcode, users in q.items():
        b = find_book(conn, barcode)
        if not b:
            continue
        for i, uid in enumerate(users):
            u = rows(conn, "SELECT USER_CODE, USER_NAME, PHONE_NUMBER, ADDRESS FROM USERS WHERE USER_CODE=? AND DELETE_YN='N'", uid)
            if u:
                out.append({"book": b, "position": i + 1, "holdUntil": "",
                            "user": {"userId": uid, "userName": u[0]["USER_NAME"] or "",
                                     "phone": u[0]["PHONE_NUMBER"] or "", "address": u[0]["ADDRESS"] or ""}})
    return out


# ---- members ------------------------------------------------------------

USER_SQL = """
SELECT U.USER_CODE, U.USER_NAME, U.PHONE_NUMBER, U.ADDRESS, U.EMAIL, U.USER_LEVEL, U.NOTICE,
       U.DISABLE_DATE, U.DELAY_CHARGE, U.REG_DATE, U.USER_IMAGE,
       (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='000' AND SUB_CODE=U.USER_LEVEL) AS GRADE_NAME,
       (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='003' AND SUB_CODE=U.USER_STATE) AS STATE_NAME,
       G.RENTAL_DATE, G.RENTAL_MAX, G.RESERVE_MAX
FROM USERS AS U LEFT JOIN USER_LEVEL AS G ON G.CODE_NUMBER = U.USER_LEVEL
WHERE U.DELETE_YN = 'N'
"""


def user_base(r):
    suspend = d10(r["DISABLE_DATE"])
    memo = "\n".join(x for x in [(r["NOTICE"] or "").strip(), suspend and f"대출정지일 : {suspend} 까지"] if x)
    return {"userId": r["USER_CODE"], "userName": (r["USER_NAME"] or "").strip(), "phone": r["PHONE_NUMBER"] or "",
            "address": r["ADDRESS"] or "", "email": r["EMAIL"] or "", "userGrade": (r["GRADE_NAME"] or "").strip(),
            "userState": (r["STATE_NAME"] or "").strip(), "memo": memo, "suspendUntil": suspend,
            "unpaid": r["DELAY_CHARGE"] or 0, "regDate": d10(r["REG_DATE"]), "photo": (r["USER_IMAGE"] or "").strip(),
            "lendDays": r["RENTAL_DATE"] or 0, "maxLend": r["RENTAL_MAX"] or 0, "maxReserve": r["RESERVE_MAX"] or 0}


def find_user(conn, user_id):
    found = rows(conn, USER_SQL + " AND U.USER_CODE = ?", user_id.strip().upper())
    if not found:
        return None
    user = user_base(found[0])
    lent = rows(conn, BOOK_SQL + " AND L.USERS = ? AND L.STATS IN (1, 3) ORDER BY L.LENT_DATE", user["userId"])
    loans = []
    for r in lent:
        b = book_view(r)
        loans.append({**b["loan"], "book": b})
    reserved = []
    for r in rows(conn, "SELECT BOOK_CODE FROM RESERVATION WHERE USER_CODE = ? ORDER BY REG_DATE", user["userId"]):
        b = find_book(conn, r["BOOK_CODE"])
        if b:
            reserved.append({"book": b, "position": b["queue"].index(user["userId"]) + 1 if user["userId"] in b["queue"] else 0})
    return {**user, "loans": loans, "lentCount": len(loans), "overdue": any(l["state"] == "연체중" for l in loans),
            "reservations": reserved, "reserveCount": len(reserved)}


USER_FIELDS = {"회원번호": "U.USER_CODE", "회원명": "U.USER_NAME", "주소": "U.ADDRESS", "전화번호": "U.PHONE_NUMBER",
               "이메일": "U.EMAIL"}


def search_users(conn, field, keyword, limit=1000):
    sql, params = USER_SQL, [f"%{(keyword or '').strip()}%"]
    if field == "회원등급":
        sql += " AND (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='000' AND SUB_CODE=U.USER_LEVEL) LIKE ?"
    elif field == "회원상태":
        sql += " AND (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='003' AND SUB_CODE=U.USER_STATE) LIKE ?"
    else:
        sql += f" AND {USER_FIELDS.get(field, 'U.USER_CODE')} LIKE ?"
    found = rows(conn, sql.replace("SELECT ", f"SELECT TOP {int(limit)} ", 1) + " ORDER BY U.USER_CODE", *params)
    return [user_base(r) for r in found]


PHOTO_TYPES = {"jpg", "jpeg", "png", "gif", "bmp"}


def photo_folders():
    """Where member photos may be read from: CLIB's UserImage folder, the copy Windows keeps of
    it when CLIB isn't allowed to write to Program Files (VirtualStore), and photoDir."""
    import os
    cfg = config()
    clib = Path(cfg["clibDir"]) / "UserImage"
    folders = [clib, Path(cfg["photoDir"])]
    local = os.environ.get("LOCALAPPDATA")
    if local and clib.drive:
        folders.insert(1, Path(local) / "VirtualStore" / clib.relative_to(clib.anchor))
    return list(dict.fromkeys(f.resolve() for f in folders))


def user_photo(conn, user_id):
    """The member's photo file. USER_IMAGE holds the full path CLIB saved it to; when the file
    isn't there (photos copied over from another PC, a moved folder), a file of the same name in
    one of the photo folders is used. Only files inside those folders are served."""
    found = rows(conn, "SELECT USER_CODE, USER_IMAGE FROM USERS WHERE USER_CODE = ? AND DELETE_YN = 'N'", user_id.strip().upper())
    path = (found[0]["USER_IMAGE"] or "").strip() if found else ""
    if not path:
        return None
    folders = photo_folders()
    stored = Path(path).resolve()
    if any(f in stored.parents for f in folders) and stored.is_file():
        return stored
    name = path.replace("/", "\\").rsplit("\\", 1)[-1]
    for folder in folders:
        candidate = (folder / name).resolve()
        if folder in candidate.parents and candidate.suffix.lower().lstrip(".") in PHOTO_TYPES and candidate.is_file():
            return candidate
    return None


def users_by_name(conn, name):
    return [user_base(r) for r in rows(conn, USER_SQL + " AND U.USER_NAME = ?", (name or "").strip())]


def users_by_grade(conn, grade):
    """UserCodeDlg.SearchUser(): every member of one grade, by number."""
    found = rows(conn, """SELECT U.USER_CODE, U.USER_NAME, C.SUB_NAME FROM USERS AS U
                          JOIN CODE_SUB AS C ON C.CODE_NUMBER='000' AND C.SUB_CODE=U.USER_LEVEL
                          WHERE U.DELETE_YN='N' AND C.SUB_NAME=? ORDER BY U.USER_CODE""", (grade or "").strip())
    return [{"userGrade": (r["SUB_NAME"] or "").strip(), "userId": (r["USER_CODE"] or "").strip(),
             "userName": (r["USER_NAME"] or "").strip()} for r in found]


KDC = ["총류", "철학", "종교", "사회과학", "자연과학", "기술과학", "예술", "언어", "문학", "역사"]


def user_history(conn, user_id):
    """UserLentStats.LoadUserStats(): the member's RENTAL_HISTORY with each book, oldest first.
    The screen filters by period and kind. CLIB calls everything that isn't 대출/반납 연체, so
    its reservations (2) showed as 연체; they are 예약 here. A category that isn't a KDC number
    is left blank (CLIB says 역사)."""
    user = rows(conn, "SELECT USER_CODE, USER_NAME FROM USERS WHERE DELETE_YN='N' AND UPPER(REPLACE(USER_CODE,' ','')) = ?",
                (user_id or "").replace(" ", "").upper())
    if not user:
        return None
    found = rows(conn, """SELECT SUBSTRING(A.REG_DATE, 1, 10) AS D, A.BOOK_CODE, B.BOOKNAME, B.BOOKNUM, B.CATEGORY, A.BOOK_STATE
        FROM RENTAL_HISTORY AS A
        CROSS APPLY (SELECT TOP 1 BOOKNAME, BOOKNUM, CATEGORY FROM BOOK WHERE BARCODE = A.BOOK_CODE
                     ORDER BY CASE WHEN DELETE_YN = 'N' THEN 0 ELSE 1 END) AS B
        WHERE A.USER_CODE = ? ORDER BY A.SEQ""", user[0]["USER_CODE"])
    out = []
    for r in found:
        title, volume, cat = (r["BOOKNAME"] or "").strip(), (r["BOOKNUM"] or "").strip(), (r["CATEGORY"] or "").strip()
        out.append({"date": r["D"] or "", "barcode": r["BOOK_CODE"], "title": f"{title}. {volume}" if volume else title,
                    "category": KDC[int(cat[0])] if cat[:1].isdigit() else "", "state": HISTORY_KIND.get(r["BOOK_STATE"], "연체")})
    return {"userId": user[0]["USER_CODE"].strip(), "userName": (user[0]["USER_NAME"] or "").strip(), "rows": out}


def deleted_users(conn):
    """DeleteUsers.InitList(): deleted members, oldest deletion first, with the history recorded
    up to the deletion (RENTAL_HISTORY 1 대출, 0 반납, 3 연체). The deletion time (MOD_DATE) is
    passed back as it is to clear that history."""
    found = rows(conn, """SELECT A.USER_CODE, A.USER_NAME, A.MOD_DATE,
        (SELECT COUNT(*) FROM RENTAL_HISTORY WHERE USER_CODE=A.USER_CODE AND BOOK_STATE=1 AND REG_DATE <= A.MOD_DATE) AS LENT,
        (SELECT COUNT(*) FROM RENTAL_HISTORY WHERE USER_CODE=A.USER_CODE AND BOOK_STATE=0 AND REG_DATE <= A.MOD_DATE) AS RET,
        (SELECT COUNT(*) FROM RENTAL_HISTORY WHERE USER_CODE=A.USER_CODE AND BOOK_STATE=3 AND REG_DATE <= A.MOD_DATE) AS LATE
        FROM USERS AS A WHERE A.DELETE_YN='Y' ORDER BY A.MOD_DATE""")
    return [{"userId": (r["USER_CODE"] or "").strip(), "userName": (r["USER_NAME"] or "").strip(),
             "deleteDate": r["MOD_DATE"] or "", "lent": r["LENT"], "returned": r["RET"], "overdue": r["LATE"]}
            for r in found]


def overdue(conn):
    """BookDelay: members who are 연체중 (USER_STATE 1) with how many books they have overdue,
    and every overdue loan (BOOK_LENT STATS 3) with its borrower. USERS.DELAY_CHARGE is the
    연체금 still unpaid; the screen works out the rest from LENT_OPTION."""
    users = rows(conn, """SELECT A.USER_CODE, A.USER_NAME, A.PHONE_NUMBER, A.ADDRESS, A.EMAIL, A.DELAY_CHARGE,
        (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='000' AND SUB_CODE=A.USER_LEVEL) AS GRADE,
        (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='003' AND SUB_CODE=A.USER_STATE) AS STATE,
        (SELECT COUNT(*) FROM BOOK_LENT WHERE DELETE_YN='N' AND STATS=3 AND USERS=A.USER_CODE) AS LATE
        FROM USERS AS A WHERE A.DELETE_YN='N' AND A.USER_STATE=1 ORDER BY A.USER_CODE""")
    loans = rows(conn, """SELECT B.BARCODE, B.BOOKNAME, B.BOOKNUM, B.AUTHOR, B.EX_CATE, B.CATEGORY, B.AUTHOR_CODE,
        B.CLAIMNUM, B.COPYNUM, (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='001' AND SUB_CODE=L.STATS) AS STATE_NAME,
        L.USERS, L.LENT_DATE, L.RETURN_DATE, U.USER_NAME, U.PHONE_NUMBER, U.ADDRESS, U.EMAIL, U.DELAY_CHARGE
        FROM BOOK AS B JOIN BOOK_LENT AS L ON L.SEQ = B.SEQ
        LEFT JOIN USERS AS U ON U.USER_CODE = L.USERS AND U.DELETE_YN = 'N'
        WHERE B.DELETE_YN = 'N' AND L.DELETE_YN = 'N' AND L.STATS = 3 ORDER BY L.USERS, L.RETURN_DATE""")
    person = lambda r: {"userName": (r["USER_NAME"] or "").strip(), "phone": r["PHONE_NUMBER"] or "",
                        "address": r["ADDRESS"] or "", "email": r["EMAIL"] or "", "unpaid": r["DELAY_CHARGE"] or 0}
    return {
        "users": [{"userId": (r["USER_CODE"] or "").strip(), **person(r), "userGrade": (r["GRADE"] or "").strip(),
                   "userState": (r["STATE"] or "").strip(), "overdueCount": r["LATE"]} for r in users],
        "loans": [{"userId": (r["USERS"] or "").strip(), **person(r), "barcode": r["BARCODE"],
                   "title": (r["BOOKNAME"] or "").strip(), "volume": (r["BOOKNUM"] or "").strip(),
                   "author": (r["AUTHOR"] or "").strip(), "claim": claim(r), "bookState": (r["STATE_NAME"] or "").strip(),
                   "lentDate": d10(r["LENT_DATE"]), "dueDate": d10(r["RETURN_DATE"])} for r in loans],
    }


# ---- history ------------------------------------------------------------

def history(conn, start, end):
    found = rows(conn, """
        SELECT H.REG_DATE, H.BOOK_CODE, H.USER_CODE, H.BOOK_STATE, B.BOOKNAME, B.CATEGORY, U.USER_NAME,
               (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='000' AND SUB_CODE=U.USER_LEVEL) AS GRADE_NAME
        FROM RENTAL_HISTORY AS H
        LEFT JOIN BOOK AS B ON B.BARCODE = H.BOOK_CODE AND B.DELETE_YN = 'N'
        LEFT JOIN USERS AS U ON U.USER_CODE = H.USER_CODE AND U.DELETE_YN = 'N'
        WHERE SUBSTRING(H.REG_DATE, 1, 10) BETWEEN ? AND ?
        ORDER BY H.REG_DATE""", start, end)
    return [{"date": d10(r["REG_DATE"]), "barcode": r["BOOK_CODE"], "userId": r["USER_CODE"],
             "kind": HISTORY_KIND.get(r["BOOK_STATE"], str(r["BOOK_STATE"])), "title": (r["BOOKNAME"] or "").strip(),
             "category": (r["CATEGORY"] or "").strip(), "userName": (r["USER_NAME"] or "").strip(),
             "userGrade": (r["GRADE_NAME"] or "").strip()} for r in found]


# ---- 도서보유현황 / 이용자현황 (BookStats.cs, UserStats.cs, TotalProgerssDlg) -------------

CATEGORY_NAMES = ["000 : 총류", "100 : 철학", "200 : 종교", "300 : 사회과학", "400 : 자연과학",
                  "500 : 기술과학", "600 : 예술", "700 : 언어", "800 : 문학", "900 : 역사"]
# A class is a range of CATEGORY strings; 900 runs to CLIB's '999.99999999999'
CATEGORY_RANGES = [(f"{i}00", f"{i + 1}00" if i < 9 else "999.99999999999") for i in range(10)]
# by: 0 도서상태, 1 도서분류, 2 별치기호, 3 소장위치, 4 반입구분
BOOK_GROUPS = {0: ("001", "B.STATS"), 3: ("002", "A.LOCATION"), 4: ("004", "A.BOOKIN")}


def book_stats(conn, by):
    """Load*(): the 전체 row, then a count per state, class, 별치기호, location or 반입구분.
    도서상태 counts BOOK_LENT rows, the others BOOK rows, as CLIB does."""
    if by == 0:
        total = rows(conn, "SELECT COUNT(*) AS n FROM BOOK_LENT WHERE DELETE_YN='N'")[0]["n"]
        counts = {r["k"]: r["n"] for r in rows(conn, "SELECT STATS AS k, COUNT(*) AS n FROM BOOK_LENT WHERE DELETE_YN='N' GROUP BY STATS")}
    else:
        total = rows(conn, "SELECT COUNT(*) AS n FROM BOOK WHERE DELETE_YN='N'")[0]["n"]
    out = [{"name": "전체", "count": total}]
    if by == 1:
        for name, (lo, hi) in zip(CATEGORY_NAMES, CATEGORY_RANGES):
            n = rows(conn, "SELECT COUNT(*) AS n FROM BOOK WHERE DELETE_YN='N' AND CATEGORY >= ? AND CATEGORY < ?", lo, hi)[0]["n"]
            out.append({"name": name, "count": n})
    elif by == 2:
        for r in rows(conn, "SELECT EX_CATE AS k, COUNT(*) AS n FROM BOOK WHERE DELETE_YN='N' GROUP BY EX_CATE ORDER BY EX_CATE"):
            out.append({"name": r["k"] if r["k"] is not None else "", "count": r["n"]})
    else:
        group, column = BOOK_GROUPS[by]
        if by != 0:
            counts = {r["k"]: r["n"] for r in rows(conn, f"SELECT {column.split('.')[1]} AS k, COUNT(*) AS n FROM BOOK WHERE DELETE_YN='N' GROUP BY {column.split('.')[1]}")}
        for r in rows(conn, "SELECT SUB_CODE, SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER=? ORDER BY SUB_CODE", group):
            out.append({"name": (r["SUB_NAME"] or "").strip(), "count": counts.get(r["SUB_CODE"], 0)})
    return out


def book_stats_detail(conn, by, name, row):
    """Load*Detail(): the books of one row (전체 = every book). 도서분류 goes by the row's
    position, the others by its name."""
    sql = """SELECT (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='001' AND SUB_CODE=B.STATS) AS STATE, A.BARCODE,
                    A.BOOKNAME, A.BOOKNUM, A.AUTHOR, A.PUBLISH, A.CLAIM,
                    (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='002' AND SUB_CODE=A.LOCATION) AS BOOKLOCATION,
                    (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='004' AND SUB_CODE=A.BOOKIN) AS INBOOK,
                    SUBSTRING(A.REG_DATE, 1, 10) AS REGDATE
             FROM BOOK AS A JOIN BOOK_LENT AS B ON A.BARCODE = B.BARCODE
             WHERE A.DELETE_YN='N' AND B.DELETE_YN='N'"""
    params = []
    if by == 1:
        if row > 0:
            lo, hi = CATEGORY_RANGES[min(row, 10) - 1]
            sql += " AND A.CATEGORY >= ? AND A.CATEGORY < ?"
            params += [lo, hi]
    elif name != "전체":
        if by == 2:
            sql += " AND A.EX_CATE = ?"
            params.append(name)
        else:
            group, column = BOOK_GROUPS[by]
            code = rows(conn, "SELECT SUB_CODE FROM CODE_SUB WHERE CODE_NUMBER=? AND SUB_NAME=?", group, name)
            if not code:
                return []
            sql += f" AND {column} = ?"
            params.append(code[0]["SUB_CODE"])
    out = []
    for r in rows(conn, sql + " ORDER BY B.BARCODE", *params):
        title, volume = r["BOOKNAME"] or "", r["BOOKNUM"] or ""
        out.append({"no": len(out) + 1, "bookState": (r["STATE"] or "").strip(), "barcode": r["BARCODE"],
                    "title": f"{title}. {volume}" if volume != "" else title, "author": r["AUTHOR"] or "",
                    "publisher": r["PUBLISH"] or "", "claim": r["CLAIM"] or "", "location": (r["BOOKLOCATION"] or "").strip(),
                    "bookIn": (r["INBOOK"] or "").strip(), "regDate": r["REGDATE"] or ""})
    return out


# by: 0 회원등급 (CODE_SUB 000, USERS.USER_LEVEL), 1 회원상태 (003, USER_STATE)
USER_GROUPS = {0: ("000", "USER_LEVEL", "회원등급"), 1: ("003", "USER_STATE", "회원상태")}


def user_stats(conn, by):
    """SearchUserLevel() / SearchUserState(): the 전체 row, then a count per grade or state."""
    group, column, label = USER_GROUPS[by]
    codes = rows(conn, "SELECT SUB_CODE, SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER=? ORDER BY SUB_CODE", group)
    if not codes:
        return {"error": f"{label}{'이' if by == 0 else '가'} 잘못 설정되어있습니다."}
    counts = {r["k"]: r["n"] for r in rows(conn, f"SELECT {column} AS k, COUNT(*) AS n FROM USERS WHERE DELETE_YN='N' GROUP BY {column}")}
    out = [{"name": "전체", "count": sum(counts.values())}]
    out += [{"name": (r["SUB_NAME"] or "").strip(), "count": counts.get(r["SUB_CODE"], 0)} for r in codes]
    return {"rows": out}


def user_stats_detail(conn, by, name):
    """LoadUserLevelDetail() / LoadUserStateDetail(): the members of one row, with how many
    loans (BOOK_STATE 1) and overdue notes (3) their history holds."""
    group, column, label = USER_GROUPS[by]
    where, params = "", []
    if name != "전체":
        code = rows(conn, "SELECT SUB_CODE FROM CODE_SUB WHERE CODE_NUMBER=? AND SUB_NAME=?", group, name.strip())
        if not code:
            return {"error": f"{label}{'이' if by == 0 else '가'} 잘못 설정되었습니다."}
        where, params = f" AND A.{column} = ?", [code[0]["SUB_CODE"]]
    sql = f"""SELECT (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='000' AND SUB_CODE=A.USER_LEVEL) AS GRADE,
                     (SELECT SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='003' AND SUB_CODE=A.USER_STATE) AS STATE,
                     A.USER_CODE, A.USER_NAME, A.PHONE_NUMBER, A.ADDRESS, A.EMAIL,
                     (SELECT COUNT(*) FROM RENTAL_HISTORY WHERE USER_CODE=A.USER_CODE AND BOOK_STATE=1) AS LENT,
                     (SELECT COUNT(*) FROM RENTAL_HISTORY WHERE USER_CODE=A.USER_CODE AND BOOK_STATE=3) AS LATE,
                     SUBSTRING(A.DISABLE_DATE, 1, 10) AS STOP, SUBSTRING(A.REG_DATE, 1, 10) AS REGDATE
              FROM USERS AS A WHERE A.DELETE_YN='N'{where} ORDER BY A.USER_CODE"""
    out = []
    for r in rows(conn, sql, *params):
        out.append({"no": len(out) + 1, "userGrade": (r["GRADE"] or "").strip(), "userState": (r["STATE"] or "").strip(),
                    "userId": r["USER_CODE"], "userName": r["USER_NAME"] or "", "phone": r["PHONE_NUMBER"] or "",
                    "address": r["ADDRESS"] or "", "email": r["EMAIL"] or "", "totalLent": r["LENT"],
                    "totalOverdue": r["LATE"], "suspendUntil": r["STOP"] or "", "regDate": r["REGDATE"] or ""})
    return {"rows": out}
