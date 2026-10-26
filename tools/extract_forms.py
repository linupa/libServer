"""Extract the control layout (labels, text boxes, buttons, combo boxes, group boxes,
tabs, lists) of selected CLIB forms from decompiled source and write web/js/forms.js.

Usage: python3 tools/extract_forms.py <CLIB_decompiled dir> [web/js/forms.js]
"""
import json
import re
import sys
from pathlib import Path

BANNERS = ["picture_repair", "picture_shop", "picture_remote", "picture_board"]

# form class -> source file, controls to drop
FORMS = {
    # btn_RFID_*: hidden unless an RFID reader is attached; picture_*: vendor banner ads
    "BookLent": {"file": "BookDream/BookLent.cs", "skip": BANNERS + ["btn_RFID_User", "btn_RFID_Book"]},
    "BookReturn": {"file": "BookDream/BookReturn.cs", "skip": BANNERS + ["btn_RFID_User", "btn_RFID_Book"]},
    "BookReserve": {"file": "BookDream/BookReserve.cs", "skip": BANNERS + ["btn_RFID_User", "btn_RFID_Book"]},
    # panel2 holds the banner ads; btn_tagging/button1 are RFID-only
    "BookManage": {"file": "BookDream/BookManage.cs", "skip": ["panel2", "btn_tagging", "button1"]},
    # 전체선택 is replaced on the web by 전체 불러오기 (load every result)
    "SearchMarc": {"file": "BookDream/SearchMarc.cs", "skip": ["btn_AllCheck"]},
    "Users": {"file": "BookDream/Users.cs", "skip": BANNERS},
    "UserSearch": {"file": "BookDream/UserSearch.cs", "skip": ["btn_sel"]},
    # btn_search is a hidden helper button in the corner
    "Lent_ReturnStats": {"file": "BookDream.STATS/Lent_ReturnStats.cs", "skip": []},
    # 도서보유현황 / 이용자현황: totals on the left, the books or members of a row on the right
    "BookStats": {"file": "BookDream.STATS/BookStats.cs", "skip": []},
    "UserStats": {"file": "BookDream.STATS/UserStats.cs", "skip": []},
    "SelectUserCard": {"file": "BookDream.User/SelectUserCard.cs", "skip": []},
    "UserCardPrint": {"file": "BookDream.Print/UserCardPrint.cs", "skip": []},
    # 청구기호 출력: label options for the books checked in 도서관리
    "ClaimPrint": {"file": "BookDream.Print/ClaimPrint.cs", "skip": []},
    # The half-second notice after 대출 / 반납 / 예약
    "LentMsg": {"file": "BookDream.Lent_Return/LentMsg.cs", "skip": []},
    # 이용현황: a SplitContainer whose top half has the search controls
    "LentStats": {"file": "BookDream.Lent_Return/LentStats.cs", "skip": []},
    # Settings: four option panels, shown alone in their own dialogs or as tabs of 환경설정
    "LentOption": {"file": "BookDream.Lent_Return.Option/LentOption.cs", "skip": []},
    "UserOption": {"file": "BookDream.User.Option/UserOption.cs", "skip": []},
    # dataGridView2 is a hidden copy of the location list
    "BookOption": {"file": "BookDream.Book.Option/BookOption.cs", "skip": ["dataGridView2"]},
    "BankBookOption": {"file": "BookDream.BankBook.Option/BankBookOption.cs", "skip": []},
    "LentOptionDlg": {"file": "BookDream.Lent_Return.Option/LentOptionDlg.cs", "skip": []},
    "UserOptionDlg": {"file": "BookDream.User.Option/UserOptionDlg.cs", "skip": []},
    "BookOptionDlg": {"file": "BookDream.Book.Option/BookOptionDlg.cs", "skip": []},
    "BankBookOptionDlg": {"file": "BookDream.BankBook.Option/BankBookOptionDlg.cs", "skip": []},
    # tabPage5 (RFID 설정) is removed at runtime when no RFID reader is set up
    "OptionDlg": {"file": "BookDream.Common/OptionDlg.cs", "skip": ["tabPage5"]},
    # 연체관리: three grids in one place, one shown at a time
    "BookDelay": {"file": "BookDream/BookDelay.cs", "skip": []},
    # 파일로 저장: Marc 파일 저장 asks about line breaks first; both show the progress window
    "CRLFDlg": {"file": "BookDream.Book.SaveFile/CRLFDlg.cs", "skip": []},
    "SaveFileProcess": {"file": "BookDream.Book.SaveFile/SaveFileProcess.cs", "skip": []},
    # 회원관리 일괄수정: one dialog, opened for 회원상태 or 회원등급 (UserBatchDlg(mode))
    "UserBatchState": {"file": "BookDream.User.Batch/UserBatchDlg.cs", "skip": []},
    "UserBatchLevel": {"file": "BookDream.User.Batch/UserBatchDlg.cs", "skip": []},
    "UserCodeDlg": {"file": "BookDream.User/UserCodeDlg.cs", "skip": []},
    "DeleteUsers": {"file": "BookDream.User/DeleteUsers.cs", "skip": []},
    # 회원관리's own buttons: 회원일괄입력, 이용내역 조회, 가입신청서 출력
    "BatchInput": {"file": "BookDream.User.Batch/BatchInput.cs", "skip": []},
    "UserLentStats": {"file": "BookDream.STATS/UserLentStats.cs", "skip": []},
    "JoinPrint": {"file": "BookDream.Print/JoinPrint.cs", "skip": []},
    # 데이터베이스 관리 > 자동백업설정
    "Set_Backup": {"file": "BookDream.BakcupOption/Set_Backup.cs", "skip": []},
}

TYPES = {"Label": "label", "TextBox": "text", "RichTextBox": "text", "Button": "button",
         "GroupBox": "group", "Panel": "panel", "ListView": "list", "DataGridView": "list",
         "PictureBox": "picture", "ComboBox": "combo", "CheckBox": "check",
         "RadioButton": "radio", "TabControl": "tabs", "TabPage": "tabpage",
         "DateTimePicker": "date", "TableLayoutPanel": "panel", "SplitContainer": "panel",
         "ProgressBar": "progress"}


def color(value):
    if not value:
        return None
    m = re.search(r"FromArgb\((\d+), (\d+), (\d+)\)", value)
    if m:
        return "rgb({}, {}, {})".format(*m.groups())
    m = re.search(r"Color\.(\w+)", value)
    # CSS knows the .NET named colours (LightSteelBlue, Khaki, Bisque, ...)
    return m.group(1).lower() if m else None


def extract(path, skip):
    src = path.read_text(encoding="utf-8")
    init = src[src.index("private void InitializeComponent()"):]
    types = dict((n, t) for t, n in re.findall(r"private (\w+) (\w+);", src))

    props = {}
    for name, prop, val in re.findall(r"\(\(\w+\)(\w+)\)\.(\w+) = (.+?);\n", init) + \
            re.findall(r"\n\t\t(\w+)\.(\w+) = (.+?);\n", init):
        props.setdefault(name, {})[prop] = val

    items = {}
    for name, body in re.findall(r"\b(\w+)\.Items\.AddRange\(new object\[\d+\]\s*\{(.*?)\}\);", init, re.S):
        items[name] = re.findall(r'"([^"]*)"', body)

    children = {}
    # A SplitContainer's Panel1/Panel2 children belong to the container itself
    for parent, child in re.findall(r"\(\((?:Control)\)(\w+)(?:\.Panel[12])?\)\.Controls\.Add\(\(Control\)(?:\(object\))?(\w+)\)", init):
        children.setdefault(parent, []).append(child)
    # TabControl pages are added through TabPages
    for parent, child in re.findall(r"\b(\w+)\.TabPages\.Add\(\(?\w*\)?(\w+)\)", init):
        children.setdefault(parent, []).append(child)

    def node(name):
        p = props.get(name, {})
        kind = TYPES.get(types.get(name, ""), "other")
        loc = re.search(r"(\d+), (\d+)", p.get("Location", "0, 0"))
        size = re.search(r"(\d+), (\d+)", p.get("Size", "0, 0"))
        text = re.match(r'"(.*)"$', p.get("Text", ""))
        n = {"id": name, "type": kind,
             "x": int(loc.group(1)), "y": int(loc.group(2)),
             "w": int(size.group(1)), "h": int(size.group(2))}
        if text and (kind != "text" or text.group(1)):
            n["text"] = text.group(1).replace("\\r\\n", "\n")
        if p.get("ReadOnly") == "true" and kind != "list":
            n["readOnly"] = True
        if p.get("Multiline") == "true" or types.get(name) == "RichTextBox":
            n["multiline"] = True
        if p.get("Visible") == "false":
            n["hidden"] = True
        if p.get("Appearance") == "(Appearance)1":
            n["pushLike"] = True
        if p.get("Checked") == "true":
            n["checked"] = True
        # ContentAlignment: 1/2/4 Top, 16/32/64 Middle, 256/512/1024 Bottom (Left/Center/Right)
        m = re.search(r"\(ContentAlignment\)(\d+)", p.get("TextAlign", ""))
        if m and kind in ("label", "button", "radio", "check"):
            a = int(m.group(1))
            n["align"] = ["left", "center", "right"][(a.bit_length() - 1) % 4 if a < 16 else ((a.bit_length() - 1) - 4) % 4 if a < 256 else ((a.bit_length() - 1) - 8) % 4]
            n["valign"] = "top" if a < 16 else "middle" if a < 256 else "bottom"
        if re.search(r"\(FontStyle\)1", p.get("Font", "")):
            n["bold"] = True
        if color(p.get("BackColor")) and kind not in ("list",):
            n["back"] = color(p.get("BackColor"))
        if color(p.get("ForeColor")):
            n["fore"] = color(p.get("ForeColor"))
        if kind == "combo":
            n["items"] = items.get(name, [])
            # ComboBoxStyle 2 = DropDownList (pick only)
            if "(ComboBoxStyle)2" in p.get("DropDownStyle", ""):
                n["dropDownList"] = True
        kids = [node(c) for c in children.get(name, []) if c not in skip]
        if kids:
            if kind == "tabs":
                n["children"] = kids  # keep tab order
            else:
                # WinForms adds children in reverse z-order; sort by position for reading order
                n["children"] = sorted(kids, key=lambda k: (k["y"], k["x"]))
        return n

    form = props.get("this", {})
    # UserControls (the option panels) have a Size instead of a ClientSize
    size = re.search(r"(\d+), (\d+)", form.get("ClientSize") or form.get("Size", "0, 0"))
    title = re.match(r'"(.*)"$', form.get("Text", ""))
    return {
        "title": title.group(1).strip("[]") if title else "",
        "w": int(size.group(1)), "h": int(size.group(2)),
        "backColor": color(form.get("BackColor")),
        # A bold form font is inherited by every control
        "bold": bool(re.search(r"\(FontStyle\)1", form.get("Font", ""))),
        "children": sorted([node(c) for c in children.get("this", []) if c not in skip],
                           key=lambda k: (k["y"], k["x"])),
    }


def main():
    root = Path(sys.argv[1])
    out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent.parent / "web/js/forms.js")
    forms = {name: extract(root / spec["file"], set(spec["skip"])) for name, spec in FORMS.items()}
    body = json.dumps(forms, ensure_ascii=False, indent=1)
    out.write_text("// Generated by tools/extract_forms.py from decompiled CLIB. Do not edit.\n"
                   f"window.CLIB_FORMS = {body};\n", encoding="utf-8")
    print(f"{len(forms)} forms -> {out}")


if __name__ == "__main__":
    main()
