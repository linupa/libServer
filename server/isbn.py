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
        author = re.sub(rf"\s+{re.escape(role)}(?=,|$)", "", author)
    return re.sub(r",{2,}", ",", author).strip(" ,")


def search_seoji(isbn, key, book):
    """SearchISBNBook(): True when seoji knows the ISBN."""
    data = json.loads(fetch(SEOJI_URL, {"cert_key": key, "result_style": "json", "page_no": 1, "page_size": 10,
                                        "isbn": isbn}))
    if data.get("RESULT") == "ERROR":
        raise IsbnError(f"국립중앙도서관 서지정보 검색 오류: {data.get('ERR_MESSAGE') or data.get('ERR_CODE')}")
    if str(data.get("TOTAL_COUNT", "0")) == "0" or not data.get("docs"):
        return False
    doc = {k: (v or "").strip() if isinstance(v, str) else v for k, v in data["docs"][0].items()}
    book.update(seriesTitle=doc.get("SERIES_TITLE", ""), volume=doc.get("VOL", ""), pages=doc.get("PAGE", ""),
                size=doc.get("BOOK_SIZE", ""), price=doc.get("PRE_PRICE", ""),
                claimVolume=doc.get("SERIES_NO", "") or doc.get("VOL", ""), title=doc.get("TITLE", ""),
                category=doc.get("KDC", ""), author=clean_author(doc.get("AUTHOR", "")),
                publisher=doc.get("PUBLISHER", "").replace("&page :", "").strip())
    add_code = doc.get("EA_ADD_CODE", "")
    if not book["category"] and len(add_code) == 5:
        book["category"] = add_code[2:5]  # the ISBN add-on code ends with the KDC class
    if len(doc.get("PUBLISH_PREDATE", "")) > 4:
        book["year"] = doc["PUBLISH_PREDATE"][:4]
    book["isbn"] = re.sub(r"</?b>", "", doc.get("EA_ISBN", "")).strip() or isbn
    return True


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
