"""ISBN search, ported from BookManage.SearchToISBN() (도서관리설정 ISBN 검색: 국립중앙도서관) by
way of libServer's isbnLookup.py.

Three National Library of Korea Open APIs, as CLIB calls them: 서지정보유통지원시스템 (seoji)
for the book itself, the 국립중앙도서관 catalogue for what seoji left empty and the 분류기호,
and KOLIS-NET for the latest publication year among the libraries holding it. CLIB's other
mode (SearchISBNDlg) used the key-less kolisnet/openApi/open.php, which no longer answers.

The API key is not in the code: it is read from a JSON file, C:\\CLIB\\isbnKey.json unless
config.json names another ("isbnKeyFile"):
    {"key": "<nl.go.kr Open API key>"}
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from db import config

DEFAULT_KEY_FILE = r"C:\CLIB\isbnKey.json"
SEOJI_URL = "https://www.nl.go.kr/seoji/SearchApi.do"
NL_SEARCH_URL = "https://www.nl.go.kr/NL/search/openApi/search.do"
KOLISNET_URL = "https://www.nl.go.kr/NL/search/openApi/searchKolisNet.do"

AUTHOR_ROLES = ["지음", "옮김", "엮음", "엮은이", "글쓴이", "번역", "지은이",
                "이름", "성명", "저자", "글·그림", "글·사진", "글", "그림"]


class IsbnError(Exception):
    """A failure to show as it is (no key, the library's API refusing the key)."""


def api_key():
    path = Path(config().get("isbnKeyFile") or DEFAULT_KEY_FILE)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise IsbnError(f"ISBN 검색 키 파일이 없습니다.\n{path}") from None
    except (OSError, ValueError) as e:
        raise IsbnError(f"ISBN 검색 키 파일을 읽지 못했습니다.\n{path}\n{e}") from None
    key = (data.get("key") or data.get("kolisKey") or "").strip() if isinstance(data, dict) else ""
    if not key:
        raise IsbnError(f"ISBN 검색 키 파일에 \"key\"가 없습니다.\n{path}")
    return key


def fetch(url, params):
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=30) as response:
        return response.read()


def clean_author(author):
    """ChkAuthor(): drop role words such as "지음 :" and make ";" a ",". Unlike CLIB, a role word
    before a comma leaves the comma ("한강 지음, 김철수 옮김" is two people), and one ending the
    text goes too ("한강 지음", as seoji gives it)."""
    author = re.sub(r"\s*[,;]\s*", ",", author)
    for role in AUTHOR_ROLES:
        author = re.sub(rf"{re.escape(role)}\s*:\s*", "", author)
        author = re.sub(rf"\s+{re.escape(role)}\.?(?=,|$)", "", author)
    return re.sub(r",{2,}", ",", author).strip(" ,")


def seoji_docs(key, **query):
    """서지정보 records for an isbn= or title= query (up to 10)."""
    data = json.loads(fetch(SEOJI_URL, {"cert_key": key, "result_style": "json", "page_no": 1, "page_size": 10,
                                        **query}))
    if data.get("RESULT") == "ERROR":
        raise IsbnError(f"국립중앙도서관 서지정보 검색 오류: {data.get('ERR_MESSAGE') or data.get('ERR_CODE')}")
    if str(data.get("TOTAL_COUNT", "0")) == "0":
        return []
    return [{k: (v or "").strip() if isinstance(v, str) else v for k, v in d.items()} for d in data.get("docs") or []]


def seoji_fields(doc, isbn=""):
    """The fields SearchISBNBook() takes from one 서지정보 record."""
    book = dict(seriesTitle=doc.get("SERIES_TITLE", ""), volume=doc.get("VOL", ""), pages=doc.get("PAGE", ""),
                size=doc.get("BOOK_SIZE", ""),
                # 예정가격, which CLIB reads; the 재정가 when the publisher gave only that
                price=(doc.get("PRE_PRICE", "") or doc.get("REAL_PRICE", "")).replace(",", ""),
                claimVolume=doc.get("SERIES_NO", "") or doc.get("VOL", ""), title=re.sub(r"\s+", " ", doc.get("TITLE", "")),
                category=doc.get("KDC", ""), author=clean_author(doc.get("AUTHOR", "")),
                publisher=doc.get("PUBLISHER", "").replace("&page :", "").strip(), year="")
    add_code = doc.get("EA_ADD_CODE", "")
    if not book["category"] and len(add_code) == 5:
        book["category"] = add_code[2:5]  # the ISBN add-on code ends with the KDC class
    if len(doc.get("PUBLISH_PREDATE", "")) > 4:
        book["year"] = doc["PUBLISH_PREDATE"][:4]
    book["isbn"] = re.sub(r"</?b>", "", doc.get("EA_ISBN", "")).strip() or isbn
    return book


def search_seoji(isbn, key, book):
    """SearchISBNBook(): True when seoji knows the ISBN."""
    docs = seoji_docs(key, isbn=isbn)
    if docs:
        book.update(seoji_fields(docs[0], isbn))
    return bool(docs)


def items(url, params):
    root = ET.fromstring(fetch(url, params))
    # A refused key comes back as <error><msg>INVALID KEY:…</msg><error_code>011</error_code></error>
    error = root if root.tag == "error" else root.find(".//error")
    if error is not None:
        raise IsbnError(f"국립중앙도서관 검색 오류: {(error.findtext('msg') or error.findtext('error_code') or '').strip()}")
    if int(root.findtext(".//paramData/total", "0") or 0) <= 0:
        return []
    return root.findall(".//item")


def search_nl(isbn, key, book):
    """SearchNLBook(): fills only what seoji left empty, and takes its 분류기호."""
    found = items(NL_SEARCH_URL, {"key": key, "kwd": isbn, "pageNum": 1, "pageSize": 10, "systemType": "오프라인자료"})
    if not found:
        return False
    text = lambda tag: (found[0].findtext(tag) or "").strip()
    for field, tag in (("title", "title_info"), ("publisher", "pub_info"), ("year", "pub_year_info")):
        if not book[field]:
            book[field] = text(tag)
    if not book["author"]:
        book["author"] = clean_author(text("author_info"))
    if text("class_no"):
        book["category"] = text("class_no")
    return True


def search_kolisnet(isbn, key, book):
    """SearchKolisNet(): the latest publication year among the holdings."""
    years = [(i.findtext("pub_year_info") or "").strip()
             for i in items(KOLISNET_URL, {"key": key, "kwd": isbn, "pageNum": 1, "pageSize": 50})]
    if any(years):
        book["year"] = max(y for y in years if y)


def lookup(isbn):
    """SearchToISBN(): the book's fields as 도서관리 names them, or None when nothing is found.
    Raises IsbnError for a missing key or an API error, OSError when nl.go.kr can't be reached."""
    isbn = re.sub(r"[\s-]", "", isbn)
    key = api_key()
    book = dict.fromkeys(("isbn", "title", "volume", "seriesTitle", "claimVolume", "author", "publisher", "year",
                          "category", "pages", "size", "price"), "")
    book["isbn"] = isbn
    found_seoji = search_seoji(isbn, key, book)
    # Like CLIB, the catalogue is searched by the ISBN seoji gave back
    found_nl = search_nl(book["isbn"], key, book)
    if not found_seoji and not found_nl:
        return None
    try:
        search_kolisnet(isbn, key, book)
    except (OSError, ET.ParseError):
        pass  # only the year; what was found stands
    return book


# ---- 도서 ISBN 검색 (SearchISBNDlg): every match, to pick one -------------------------------

ENTRY_FIELDS = ("isbn", "title", "volume", "seriesTitle", "claimVolume", "author", "pubPlace", "publisher", "year",
                "category", "pages", "size", "price", "bookType", "source", "detail")


def is_isbn(text):
    return bool(re.fullmatch(r"\d{9}[\dXx]|\d{13}", text))


def first_year(text):
    found = re.search(r"\d{4}", text or "")
    return found.group(0) if found else ""


def item_entry(item, source, isbn=""):
    """A catalogue or KOLIS-NET <item> as an entry."""
    text = lambda tag: re.sub(r"\s{2,}", " ", re.sub(r"</?b>", "", item.findtext(tag) or "")).strip()
    entry = dict.fromkeys(ENTRY_FIELDS, "")
    # Some catalogue items give several ISBNs (a set): the first is the book's
    isbns = text("isbn").split()
    entry.update(isbn=isbns[0] if isbns else isbn, title=text("title_info"), author=clean_author(text("author_info")),
                 publisher=re.sub(r"^[\s:]+", "", text("pub_info")), year=first_year(text("pub_year_info")),
                 category=text("class_no"), bookType=text("type_name"), source=source)
    # "서명 . 2": the 서명권차 after the last period, also the 청구권차 when a number (booklist_Click)
    volume = re.fullmatch(r"(.*\S)\s*\.\s*(\S+)", entry["title"])
    if volume:
        entry.update(title=volume.group(1), volume=volume.group(2))
        if volume.group(2).isdigit():
            entry["claimVolume"] = volume.group(2)
    entry["detail"] = "\n".join(f"{name} : {value}" for name, value in (
        ("표제사항", text("title_info")), ("저자사항", text("author_info")), ("발행사항", text("pub_info")),
        ("발행년도", text("pub_year_info")), ("청구기호", text("call_no")), ("자료구분", text("type_name"))) if value)
    return entry


def seoji_entry(doc):
    entry = dict.fromkeys(ENTRY_FIELDS, "")
    entry.update(seoji_fields(doc), bookType="도서", source="서지정보")
    entry["detail"] = "\n".join(f"{name} : {value}" for name, value in (
        ("표제사항", doc.get("TITLE", "")), ("저자사항", doc.get("AUTHOR", "")), ("발행사항", doc.get("PUBLISHER", "")),
        ("발행예정일", doc.get("PUBLISH_PREDATE", "")), ("형태사항", " ; ".join(v for v in (doc.get("PAGE", ""), doc.get("BOOK_SIZE", "")) if v)),
        ("총서사항", " ; ".join(v for v in (doc.get("SERIES_TITLE", ""), doc.get("SERIES_NO", "")) if v)),
        ("가격", doc.get("PRE_PRICE", "") or doc.get("REAL_PRICE", ""))) if value)
    return entry


def search(query):
    """SearchISBN() in 도서 ISBN 검색: every record for an ISBN in 서지정보, the 국립중앙도서관
    catalogue and KOLIS-NET (the national union catalogue CLIB's own search used), or, as CLIB
    does when an ISBN finds nothing, for the text as a title. Entries with an ISBN get what
    서지정보 knows of it (pages, size, price, series) where their own record is silent.
    Returns {"by": "isbn" | "title", "entries": [...]}."""
    query = query.strip()
    code = re.sub(r"[\s-]", "", query)
    key = api_key()

    def collect(by):
        value = code if by == "isbn" else query
        isbn_ = code if by == "isbn" else ""
        docs = seoji_docs(key, **{by: value})
        nl = items(NL_SEARCH_URL, {"key": key, "kwd": value, "pageNum": 1, "pageSize": 20, "systemType": "오프라인자료"})
        kolis = items(KOLISNET_URL, {"key": key, "kwd": value, "pageNum": 1, "pageSize": 50})
        catalogue = [item_entry(i, "국립중앙도서관", isbn_) for i in nl] + [item_entry(i, "KOLIS-NET", isbn_) for i in kolis]
        # 서지정보 matches a title loosely: its records come last there, first for an ISBN
        seoji = [seoji_entry(d) for d in docs]
        return (seoji + catalogue if by == "isbn" else catalogue + seoji), docs

    by = "isbn" if is_isbn(code) else "title"
    entries, docs = collect(by)
    if not entries and by == "isbn":
        by = "title"
        entries, docs = collect(by)

    # The same record from two sources is listed once
    seen, unique = set(), []
    for e in entries:
        mark = (re.sub(r"\W", "", e["title"]), e["volume"], re.sub(r"\W", "", e["publisher"]), e["year"], e["isbn"])
        if mark not in seen:
            seen.add(mark)
            unique.append(e)

    known = {}
    for d in docs:
        f = seoji_fields(d)
        if f["isbn"]:  # a set (no ISBN of its own) says nothing about other records
            known.setdefault(f["isbn"], f)
    missing_isbns = {e["isbn"] for e in unique if e["isbn"] and e["isbn"] not in known}
    for code_ in list(missing_isbns)[:10]:  # one 서지정보 request each; titles can list many
        try:
            found = seoji_docs(key, isbn=code_)
        except (IsbnError, OSError, ValueError):
            continue
        if found:
            known[code_] = seoji_fields(found[0], code_)
    # The catalogue's 분류기호 (813.62) is finer than the one from the ISBN add-on code (810)
    classes = {}
    for e in unique:
        if e["source"] == "국립중앙도서관" and e["isbn"] and e["category"]:
            classes.setdefault(e["isbn"], e["category"])
    for e in unique:
        if e["source"] != "국립중앙도서관" and e["isbn"] in classes and not (e["source"] == "KOLIS-NET" and e["category"]):
            e["category"] = classes[e["isbn"]]
        extra = known.get(e["isbn"]) or {} if e["isbn"] else {}
        for field in ("seriesTitle", "volume", "claimVolume", "pages", "size", "price", "category"):
            if not e[field] and extra.get(field):
                e[field] = extra[field]
    for i, e in enumerate(unique, 1):
        e["no"] = i
    return {"by": by, "entries": unique}
