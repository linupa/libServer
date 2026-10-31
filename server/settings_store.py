"""Saving settings, ported from LentOption.SaveLentOption(), UserOption.SaveUserLevel(),
BookOption (locations and its CLIB.exe.Config keys), BankBookOption, OptionDlg (도서관 설정)
UserCardPrint (card notice and margins) and ClaimPrint (label options).

Database settings are written where CLIB keeps them. The settings CLIB keeps in
CLIB.exe.Config (USERCODE, AUTHORCODE, AUTHOR, BOOK, MOUM, TOTAL, PUBLISH, ISBN_SEARCH,
CARD_*) are NOT written there: that file sits read-only in Program Files and holds CLIB's
connection settings. They go to clib_settings.json next to this
file, which is read on top of CLIB.exe.Config.
"""
import json
from pathlib import Path

from circulation import execute, one
from db import rows

OVERLAY = Path(__file__).resolve().parent / "clib_settings.json"


def overlay():
    return json.loads(OVERLAY.read_text(encoding="utf-8")) if OVERLAY.exists() else {}


def write_overlay(values):
    data = {**overlay(), **{k: str(v) for k, v in values.items()}}
    OVERLAY.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def as_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def save_settings(conn, changes):
    """changes holds any of: lend, grades, userCodeByGrade, book, bankbook, library, card, claim.
    Returns { error } or { ok, config } (config = CLIB.exe.Config values to write afterwards)."""
    config = {}

    # ---- 대출환경설정: LENT_OPTION
    if "lend" in changes:
        L = changes["lend"]
        execute(conn, """UPDATE LENT_OPTION SET LENTDATE=?, DELAY=?, DELAYDATE=?, DELAY_CHARGE=?, DELAY_MAX=?,
                         DISABLE_CHK=?, EXTEND=?, EXTEND_DAY=?, EXTEND_MAX=?, RESERVE=?, RESERVE_DAY=?, RESERVE_MAX=?,
                         DELAY_LENT=?, ATTACH=?, RE_LENT=?, RELENT_ENABLE=?, RELENT_DAY=?""",
                int(bool(L.get("includeLentDay"))), as_int(L.get("delay")), as_int(L.get("delayBasis")),
                as_int(L.get("delayCharge")), as_int(L.get("delayChargeMax")), int(bool(L.get("chargeSuspend"))),
                as_int(L.get("extend")), as_int(L.get("extendDays")), as_int(L.get("extendMax")),
                as_int(L.get("reserve")), as_int(L.get("reserveDays")), as_int(L.get("reserveMax")),
                int(bool(L.get("delayLent"))), int(bool(L.get("attach"))), int(bool(L.get("relentConfirm"))),
                int(bool(L.get("relentBan"))), as_int(L.get("relentDays"), 1))

    # ---- 회원등급설정 / 대출기간설정: CODE_SUB 000 and USER_LEVEL
    if "grades" in changes:
        grades = changes["grades"]
        if not grades:
            return {"error": "회원등급은 최소 1개 이상 사용하여야 합니다."}
        names = [(g.get("name") or "").strip() for g in grades]
        if any(not n for n in names):
            return {"error": "회원등급명을 입력해주세요."}
        if changes.get("userCodeByGrade") and any(not (g.get("prefix") or "").strip() for g in grades):
            return {"error": "구분기호를 입력해주세요."}
        if len(set(names)) != len(names):
            return {"error": "같은 회원등급명은 1개만 사용할 수 있습니다."}
        codes = [as_int(g.get("code")) for g in grades]
        # CLIB deletes a removed grade even when members still have it, leaving them without a grade
        for gone in rows(conn, "SELECT SUB_CODE, SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='000'"):
            if gone["SUB_CODE"] not in codes and one(conn, "SELECT COUNT(*) AS n FROM USERS WHERE DELETE_YN='N' AND USER_LEVEL=?",
                                                     gone["SUB_CODE"])["n"]:
                return {"error": f"'{gone['SUB_NAME'].strip()}' 등급의 회원이 있어 삭제할 수 없습니다.\n회원의 등급을 먼저 바꿔주세요."}
        for g, code, name in zip(grades, codes, names):
            prefix = (g.get("prefix") or "").strip().upper()
            if one(conn, "SELECT COUNT(*) AS n FROM CODE_SUB WHERE CODE_NUMBER='000' AND SUB_CODE=?", code)["n"]:
                execute(conn, "UPDATE CODE_SUB SET SUB_NAME=? WHERE CODE_NUMBER='000' AND SUB_CODE=?", name, code)
            else:
                execute(conn, "INSERT INTO CODE_SUB (CODE_NUMBER, SUB_CODE, SUB_NAME) VALUES ('000', ?, ?)", code, name)
            if one(conn, "SELECT COUNT(*) AS n FROM USER_LEVEL WHERE CODE_NUMBER=?", code)["n"]:
                execute(conn, "UPDATE USER_LEVEL SET CLASSIFY=? WHERE CODE_NUMBER=?", prefix, code)
                if "lendDays" in g:  # 대출기간설정 sends the limits too
                    execute(conn, "UPDATE USER_LEVEL SET RENTAL_DATE=?, RENTAL_MAX=?, RESERVE_MAX=? WHERE CODE_NUMBER=?",
                            as_int(g.get("lendDays")), as_int(g.get("maxLend")), as_int(g.get("maxReserve")), code)
            else:
                # CLIB's defaults for a new grade: 5 books, 7 days, 3 reservations
                execute(conn, "INSERT INTO USER_LEVEL (CODE_NUMBER, RENTAL_MAX, RENTAL_DATE, RESERVE_MAX, CLASSIFY) VALUES (?, 5, 7, 3, ?)",
                        code, prefix)
        placeholders = ",".join("?" * len(codes))
        execute(conn, f"DELETE FROM CODE_SUB WHERE CODE_NUMBER='000' AND SUB_CODE NOT IN ({placeholders})", *codes)
        execute(conn, f"DELETE FROM USER_LEVEL WHERE CODE_NUMBER NOT IN ({placeholders})", *codes)
    if "userCodeByGrade" in changes:
        config["USERCODE"] = "0" if changes["userCodeByGrade"] else "1"

    # ---- 도서관리설정: CLIB.exe.Config keys and CODE_SUB 002 (소장위치)
    if "book" in changes:
        B = changes["book"]
        A = B.get("authorCode") or {}
        config.update({"AUTHORCODE": as_int(A.get("table"), 5), "AUTHOR": int(bool(A.get("authorInitial"))),
                       "BOOK": int(bool(A.get("titleInitial"))), "MOUM": int(bool(A.get("moum"))),
                       "TOTAL": 0 if B.get("useSeriesTitle", True) else 1, "PUBLISH": 0 if B.get("showPublisher") else 1,
                       "ISBN_SEARCH": as_int(B.get("isbnSearch"))})
        if "locations" in B:
            locations = [(as_int(l.get("code")), (l.get("name") or "").strip()) for l in B["locations"] if (l.get("name") or "").strip()]
            if not locations:
                return {"error": "최소 1개 이상의 소장위치를 입력하여야 합니다."}
            kept = {c for c, _ in locations}
            # CLIB replaces the list even when books use a removed location; refuse that instead
            for gone in rows(conn, "SELECT SUB_CODE, SUB_NAME FROM CODE_SUB WHERE CODE_NUMBER='002'"):
                if gone["SUB_CODE"] not in kept and one(conn, "SELECT COUNT(*) AS n FROM BOOK WHERE DELETE_YN='N' AND LOCATION=?",
                                                        gone["SUB_CODE"])["n"]:
                    return {"error": f"'{gone['SUB_NAME'].strip()}' 소장위치의 도서가 있어 삭제할 수 없습니다."}
            execute(conn, "DELETE FROM CODE_SUB WHERE CODE_NUMBER='002'")
            for code, name in locations:
                execute(conn, "INSERT INTO CODE_SUB (CODE_NUMBER, SUB_CODE, SUB_NAME) VALUES ('002', ?, ?)", code, name)

    # ---- 독서통장 설정: BANKBOOK_OPTION
    if "bankbook" in changes:
        K = changes["bankbook"]
        execute(conn, """UPDATE BANKBOOK_OPTION SET LIBRARY=?, L_ADDRESS=?, PHONE=?, HOMEPAGE=?, TIME1=?, TIME2=?, TIME3=?,
                         FIRSTPRINT=?, FIRSTMSG=?, USE_YN=?, PORT=?""",
                *[(K.get(k) or "").strip() for k in ("library", "address", "phone", "homepage", "time1", "time2", "time3")],
                int(bool(K.get("greeting"))), (K.get("greetingText") or "").strip(),
                "Y" if K.get("enabled") else "N", (K.get("port") or "").strip())

    # ---- 도서관 설정: LIBRARY (the password is left alone)
    if "library" in changes:
        Lb = changes["library"]
        values = [(Lb.get(k) or "").strip() for k in ("name", "phone", "address", "email")]
        if one(conn, "SELECT COUNT(*) AS n FROM LIBRARY")["n"]:
            execute(conn, "UPDATE LIBRARY SET NAME=?, PHONE=?, ADDRESS=?, EMAIL=?", *values)
        else:
            execute(conn, "INSERT INTO LIBRARY (NAME, PHONE, ADDRESS, EMAIL, PASSWORD, NOTICE) VALUES (?,?,?,?,'','')", *values)

    # ---- 회원증 출력: LIBRARY.NOTICE (title, notice, card name with tabs) and CARD_* keys
    if "card" in changes:
        C = changes["card"]
        if any(k in C for k in ("title", "notice", "libraryName")):
            notice = "\t".join((C.get(k) or "") for k in ("title", "notice", "libraryName"))
            if one(conn, "SELECT COUNT(*) AS n FROM LIBRARY")["n"]:
                execute(conn, "UPDATE LIBRARY SET NOTICE=?", notice)
            else:
                execute(conn, "INSERT INTO LIBRARY (NAME, PHONE, ADDRESS, EMAIL, PASSWORD, NOTICE) VALUES ('','','','','',?)", notice)
        if "leftMargin" in C:
            config.update({"CARD_LEFTMARGIN": as_int(C.get("leftMargin")), "CARD_TOPMARGIN": as_int(C.get("topMargin")),
                           "CARD_OUTLINE": 1 if C.get("outline") else 0})

    # ---- 청구기호 출력: CLAIM_* keys (CLIB saves all but the skip count when printing,
    # and the v./c. check boxes as soon as they change)
    if "claim" in changes:
        K = changes["claim"]
        flag = lambda v: "1" if v else "0"
        keys = {"label": ("CLAIM_LABEL", lambda v: "1" if as_int(v) else "0"),
                "outline": ("CLAIM_OUTLINE", lambda v: "0" if v else "1"),
                "align": ("CLAIM_ALIGN", lambda v: "1" if v == "center" else "0"),
                "barcode": ("CLAIM_BARCODE", flag),
                "leftMargin": ("CLAIM_LEFTMARGIN", as_int), "topMargin": ("CLAIM_TOPMARGIN", as_int),
                "font": ("CLAIM_FONT", lambda v: 1 if as_int(v) else 0), "fontSize": ("CLAIM_FONTSIZE", lambda v: as_int(v, 10)),
                "v": ("CLAIM_V", flag), "c": ("CLAIM_C", flag), "vUpper": ("CLAIM_VUPPER", flag), "cUpper": ("CLAIM_CUPPER", flag)}
        for name, (key, convert) in keys.items():
            if name in K:
                config[key] = convert(K[name])

    return {"ok": True, "config": config}
