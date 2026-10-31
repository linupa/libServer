"""Extract every table (DataGridView / ListView) from decompiled CLIB source
and write web/js/tables.js.

Usage: python3 tools/extract_tables.py <CLIB_decompiled dir> [web/js/tables.js]
"""
import json
import re
import sys
from pathlib import Path

# Menu layout follows CLIB's TopMenu/*.cs
MENUS = [
    ("book", "도서"),
    ("user", "회원"),
    ("lent", "대출/반납"),
    ("stats", "통계"),
    ("bankbook", "독서통장"),
    ("board", "게시판"),
]

# form class -> (menu, screen title override or None)
SCREENS = {
    "BookManage": ("book", "도서관리"),
    "SearchBooks": ("book", None),
    "SearchMarc": ("book", "저장된 도서 불러오기"),
    "SearchISBNDlg": ("book", None),
    "CopyBookDlg": ("book", None),
    "CheckISBNDlg": ("book", "ISBN 중복체크"),
    "CheckClaimDlg": ("book", "청구기호 중복체크"),
    "CheckBooksDlg": ("book", None),
    "OrderBook": ("book", None),
    "BatchSaveMarcDlg": ("book", None),
    "SaveFileProcess": ("book", None),
    "TotalProgerssDlg": ("book", "전체 도서목록"),
    "MarcErrorMsg": ("book", None),
    "TagDlg": ("book", "MARC 태그"),
    "RFID_Tagging": ("book", "RFID 태깅"),
    "TagginFileOpen": ("book", None),
    "InputBarcode": ("book", "바코드 입력"),
    "BookOption": ("book", "도서관리설정"),
    "Users": ("user", "회원관리"),
    "UserSearch": ("user", None),
    "UserSelectDlg": ("user", None),
    "UserCodeDlg": ("user", "회원번호관리"),
    "DeleteUsers": ("user", "삭제번호 관리"),
    "BatchInput": ("user", None),
    "UserOption": ("user", "회원관리설정"),
    "BookLent": ("lent", "대출"),
    "BookReturn": ("lent", "반납"),
    "BookReserve": ("lent", "예약"),
    "LentFrm": ("lent", None),
    "ReservationFrm": ("lent", "예약현황"),
    "AttachFrm": ("lent", "딸림자료 대출현황"),
    "BookDelay": ("lent", None),
    "CheckLentState": ("lent", None),
    "ReturnSearch": ("lent", None),
    "LentOption": ("lent", "대출반납설정"),
    "RestDateDlg": ("lent", None),
    "Lent_ReturnStats": ("stats", "대출/반납 통계"),
    "BookStats": ("stats", None),
    "UserStats": ("stats", None),
    "UserLentStats": ("stats", None),
    "BankBookPrintDlg": ("bankbook", None),
    "BoardFrm": ("board", "게시판"),
    "LogIn": ("board", "시작화면 공지"),
}

# (form, grid) -> table label; None drops the table
TABLE_LABELS = {
    ("BookDelay", "userlist"): "연체 회원",
    ("BookDelay", "booklist"): "연체 도서",
    ("BookDelay", "delaylist"): "연체 내역",
    ("BookLent", "userlist"): "회원",
    ("BookLent", "booklist"): "대출 도서",
    ("BookReturn", "userlist"): "회원",
    ("BookReturn", "booklist"): "반납 도서",
    ("BookReserve", "userlist"): "회원",
    ("BookReserve", "booklist"): "예약 도서",
    ("BatchSaveMarcDlg", "Required_List"): "필수항목 누락",
    ("BatchSaveMarcDlg", "Overlap_List"): "중복도서",
    ("BookStats", "totallist"): "상태별 합계",
    ("BookStats", "detaillist"): "상세 목록",
    ("UserStats", "totallist"): "등급별 합계",
    ("UserStats", "detaillist"): "상세 목록",
    ("Lent_ReturnStats", "totallist"): "분류별 합계",
    ("Lent_ReturnStats", "monthlist"): "분류별 일자",
    ("Lent_ReturnStats", "bookTotallist"): "도서별 합계",
    ("Lent_ReturnStats", "bookMonthlist"): "도서별 월간",
    ("Lent_ReturnStats", "bookDatelist"): "도서별 일자",
    ("Lent_ReturnStats", "userTotallist"): "회원별 합계",
    ("Lent_ReturnStats", "userMonthlist"): "회원별 월간",
    ("Lent_ReturnStats", "userDatelist"): "회원별 일자",
    ("Lent_ReturnStats", "detaillist"): "상세 내역",
    ("Lent_ReturnStats", "numbercnt_Grid"): "일자별 이용자 수",
    ("LogIn", "listView1"): "공지사항",
    ("LogIn", "listView2"): "QNA",
    ("RestDateDlg", "listView1"): "정기휴관일",
    ("RestDateDlg", "listView2"): "임시휴관일",
    ("BookOption", "dataGridView1"): "도서소장위치",
    ("BookOption", "dataGridView2"): None,   # hidden in CLIB
    ("SearchBooks", "tmp_list"): None,       # hidden scratch list
    ("BookListPrint", "dgGrid"): None,       # copies another grid for printing
}

# Korean header -> field key, so a backend can fill rows by name
HEADER_KEYS = {
    "순번": "no", "순서": "no", "No": "no", "번호": "no", "글번호": "no",
    "등록번호": "barcode", "도서등록번호": "barcode", "도서번호": "barcode",
    "UID": "uid", "도서상태": "bookState", "서명": "title", "도서명": "title",
    "TITLE": "title", "제목": "title", "저자": "author", "지은이": "author",
    "출판사": "publisher", "분류기호": "category", "분류": "category",
    "도서분류": "category", "저자기호": "authorCode", "권차": "volume",
    "서명권차": "volume", "복본": "copy", "복본기호": "copy", "별치": "exCate",
    "별치기호": "exCate", "ISBN": "isbn", "소장위치": "location",
    "반입구분": "bookIn", "등록일": "regDate", "수정일": "modDate",
    "마크": "marc", "SEQ": "seq", "NO": "seq", "총서명": "seriesTitle",
    "회원번호": "userId", "회원명": "userName", "대출자": "borrower",
    "예약자": "reserver", "작성자": "writer", "회원등급": "userGrade",
    "회원상태": "userState", "전화번호": "phone", "연락처": "phone",
    "주소": "address", "이메일": "email", "대출기간": "lendDays",
    "최대대출권수": "maxLend", "대출권수": "maxLend",
    "최대예약권수": "maxReserve", "예약권수": "maxReserve",
    "대출일": "lendDate", "대출일자": "lendDate", "반납일": "returnDate",
    "반납일자": "returnDate", "반납예정일": "dueDate", "반납기한": "dueDate",
    "연체기간": "overdueDays", "연체도서수": "overdueCount",
    "연체금": "overdueFee", "미납금": "unpaidFee", "총 연체금": "totalFee",
    "청구기호": "claim", "대출/반납일": "date", "적요": "memo",
    "발생": "amount", "누계": "runningTotal", "출력": "print",
    "조회수": "views", "작성일": "writeDate", "마크 오류": "error",
    "분류별 순서": "orderInCategory", "위치코드": "code",
    "보안상태": "easState", "보안설정": "easSet", "보안해제": "easReset",
    "딸림자료": "attach", "반납처리": "returnAction", "예약일": "reserveDate",
    "예약순서": "reserveOrder", "예약대기 만료일": "reserveExpire",
    "취소": "cancel", "도서수": "count", "회원수": "count", "비율(%)": "ratio",
    "상태": "state", "합계": "sum", "일자": "date", "대출": "lent",
    "반납": "returned", "이용자 수": "userCount", "총 대출수": "totalLent",
    "총 연체수": "totalOverdue", "대출정지일": "suspendUntil", "□": "check",
    "삭제일": "deleteDate", "연체": "overdue", "삭제": "delete",
    "삭제취소": "undelete", "번호변경": "changeId", "실패사유": "failReason",
    "회원코드": "gradeCode", "회원등급명": "gradeName", "구분기호": "prefix",
    "내용": "content", "발행년도": "year", "출판년도": "year",
    "도서구분": "bookType", "REC_KEY": "recKey", "태그명": "tagName",
    "태그번호": "tag", "반복여부": "repeatable", "필수여부": "required",
    "휴관일": "date", "청구권차": "claimVolume", "발행지": "pubPlace",
    "페이지": "pages", "크기": "size", "가격": "price",
    "총류": "kdc0", "철학": "kdc1", "종교": "kdc2", "사회과학": "kdc3",
    "자연과학": "kdc4", "기술과학": "kdc5", "예술": "kdc6", "언어": "kdc7",
    "문학": "kdc8", "역사": "kdc9",
}

COLUMN_TYPES = {"TextBox": "text", "Header": "text", "CheckBox": "check",
                "Button": "button", "Image": "image", "ComboBox": "text"}


def extract(root):
    tables = []
    for f in sorted(root.rglob("*.cs")):
        src = f.read_text(encoding="utf-8", errors="replace")
        grids = re.findall(r"private (DataGridView|ListView) (\w+);", src)
        if not grids:
            continue
        m = re.search(r"\(\(Control\)this\)\.Text = \"([^\"]*)\"", src)
        title = m.group(1).strip("[]") if m else ""
        form = re.search(r"class (\w+)", src).group(1)
        m = re.search(r"\(\(Form\)this\)\.ClientSize = new Size\((\d+), (\d+)\)", src)
        size = [int(m.group(1)), int(m.group(2))] if m else None

        coltype = dict(re.findall(r"(\w+) = new DataGridView(\w*)Column\(\)", src))
        coltype.update((c, "Header") for c in re.findall(r"(\w+) = new ColumnHeader\(\)", src))

        def prop(col, name, pat):
            m = re.search(rf"\b{re.escape(col)}\)?\.{name} = {pat};", src)
            return m.group(1) if m else None

        for kind, grid in grids:
            m = re.search(rf"\b{grid}\.Columns\.AddRange\([^{{]*\{{(.*?)\}}\);", src, re.S)
            checkboxes = bool(re.search(rf"\b{grid}\.CheckBoxes = true;", src))
            cols = []
            for c in [c for c in re.findall(r"\w+", m.group(1)) if c in coltype] if m else []:
                textProp = "Text" if coltype[c] == "Header" else "HeaderText"
                header = prop(c, textProp, r"\"((?:[^\"\\]|\\.)*)\"") or ""
                width = prop(c, "Width", r"(\d+)")
                visible = prop(c, "Visible", r"(true|false)")
                cols.append({
                    "header": header.replace("\\r\\n", " ").replace("\\n", " ").strip(),
                    "type": COLUMN_TYPES.get(coltype[c], "text"),
                    "width": int(width) if width else None,
                    "hidden": visible == "false" or width == "0",
                })
            # A ListView with CheckBoxes draws the check in its first column
            if checkboxes and cols:
                cols[0].update(type="check", hidden=False, header="")
            tables.append({"form": form, "file": str(f.relative_to(root)),
                           "title": title, "size": size, "grid": grid, "kind": kind,
                           "columns": cols, "src": src})
    return tables


def fillDynamic(tables):
    byKey = {(t["form"], t["grid"]): t for t in tables}
    # SaveFileProcess builds its grid from the CHEADER array
    t = byKey.get(("SaveFileProcess", "dgrid"))
    if t:
        m = re.search(r"CHEADER = new string\[\d+\]\s*\{(.*?)\};", t["src"], re.S)
        t["columns"] = [{"header": h, "type": "text", "width": None, "hidden": False}
                        for h in re.findall(r"\"([^\"]*)\"", m.group(1))]
    # TotalProgerssDlg fills a DataTable with the same fields as BookStats' detail list
    t, ref = byKey.get(("TotalProgerssDlg", "dgv")), byKey.get(("BookStats", "detaillist"))
    if t and ref:
        t["columns"] = [dict(c) for c in ref["columns"]]


def assignKeys(columns):
    seen = {}
    for i, c in enumerate(columns):
        if c["type"] == "check" and not c["header"]:
            key = "checked"
        elif c["hidden"] and not c["header"]:
            # CLIB keeps a row's DB key in an unlabelled zero-width column
            key = "rowKey"
        else:
            key = HEADER_KEYS.get(c["header"]) or f"col{i}"
        n = seen.get(key, 0)
        seen[key] = n + 1
        c["key"] = key if n == 0 else f"{key}{n + 1}"


def build(tables):
    fillDynamic(tables)
    screens = {}
    for t in tables:
        label = TABLE_LABELS.get((t["form"], t["grid"]), "")
        if label is None or not t["columns"] or t["form"] not in SCREENS:
            continue
        menu, override = SCREENS[t["form"]]
        s = screens.setdefault(t["form"], {
            "id": t["form"], "menu": menu,
            "title": override or t["title"] or t["form"],
            "source": t["file"], "size": t["size"], "tables": []})
        assignKeys(t["columns"])
        s["tables"].append({"id": t["grid"], "label": label, "kind": t["kind"],
                            "columns": t["columns"]})
    order = list(SCREENS)
    return {
        "menus": [{"id": m, "label": l} for m, l in MENUS],
        "screens": sorted(screens.values(), key=lambda s: order.index(s["id"])),
    }


def main():
    root = Path(sys.argv[1])
    out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent.parent / "web/js/tables.js")
    data = build(extract(root))
    body = json.dumps(data, ensure_ascii=False, indent=1)
    out.write_text("// Generated by tools/extract_tables.py from decompiled CLIB. Do not edit.\n"
                   f"window.CLIB_UI = {body};\n", encoding="utf-8")
    n = sum(len(s["tables"]) for s in data["screens"])
    print(f"{len(data['screens'])} screens, {n} tables -> {out}")


if __name__ == "__main__":
    main()
