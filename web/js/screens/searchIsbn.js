// 도서 ISBN 검색 (SearchISBNDlg.cs): the National Library's records for an ISBN (or, when it finds
// nothing, for the text as a title), one of which goes to 도서관리 as a new record. CLIB read them
// from kolisnet/openApi/open.php, which no longer answers; the server (isbn.search) reads
// 서지정보, the 국립중앙도서관 catalogue and KOLIS-NET instead. 도서관리 searches before it opens
// this dialog (SearchISBN()), so it starts with the results.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.SearchISBNDlg = {
  ownClose: true,
  server: true,

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("booklist");

    // panel_info text box -> the field it fills in 도서관리 (btn_GetBookInfo_Click)
    const FIELDS = {
      txt_isbn: "isbn", txt_totalname: "seriesTitle", txt_bookname: "title", txt_booknamenum: "volume",
      txt_author: "author", txt_location: "pubPlace", txt_year: "year", txt_publish: "publisher",
      txt_page: "pages", txt_size: "size", txt_price: "price", txt_attach: "attach",
      txt_category: "category", txt_booknum: "claimVolume",
    };
    const BAD = "bisque";

    // InitValues()
    function clear() {
      $("txt_Detail").value = "";
      $("txt_Check").value = "";
      for (const ctl of Object.keys(FIELDS)) {
        $(ctl).value = "";
        $(ctl).style.backgroundColor = "";
      }
    }

    function show(found) {
      const rows = found.entries.map(e => ({ ...e, bookType: e.bookType || "" }));
      list.setRows(rows);
      clear();
      if (found.by === "title") $("txt_Check").value = "ISBN으로 찾지 못해 서명으로 검색한 결과입니다.";
    }

    // SearchISBN()
    async function search() {
      const query = $("txt_ISBNSearch").value.trim();
      if (!query) return ctx.msgBox("검색할 ISBN을 입력해주세요");
      $("btn_Search").disabled = true;
      try {
        const found = await lib.searchIsbn(query);
        if (found.error) return ctx.msgBox(found.error);
        if (!found.entries.length) {
          list.setRows([]);
          clear();
          return ctx.msgBox("검색결과가 없습니다.");
        }
        show(found);
      } catch (e) {
        ctx.msgBox(e.message, "도서 ISBN 검색");
      } finally {
        $("btn_Search").disabled = false;
      }
    }

    // booklist_Click(): the record's details, and its fields to check and correct
    list.onRowClick(row => {
      clear();
      $("txt_Detail").value = [`출처 : ${row.source}`, row.detail].filter(Boolean).join("\n");
      for (const [ctl, field] of Object.entries(FIELDS)) $(ctl).value = row[field] || "";
    });

    // CheckValues(): ISBN, 청구권차, 출판년도 and 분류기호 must be numbers, and the ISBN the one searched
    const isInt = v => /^-?\d+$/.test(v);
    function check() {
      const mark = (ctl, ok) => { $(ctl).style.backgroundColor = ok ? "" : BAD; };
      const isbn = $("txt_isbn").value.trim();
      mark("txt_isbn", (!isbn || isInt(isbn)) && isbn === $("txt_ISBNSearch").value.trim().replace(/-/g, ""));
      $("txt_booknum").value = $("txt_booknum").value.replace(/[[\]()]/g, "").trim();
      mark("txt_booknum", !$("txt_booknum").value || isInt($("txt_booknum").value));
      mark("txt_year", !$("txt_year").value.trim() || isInt($("txt_year").value.trim()));
      mark("txt_category", !$("txt_category").value.trim() || !isNaN(Number($("txt_category").value.trim())));
    }

    // txt_*_Click(): what the box holds, and why it is marked
    for (const ctl of Object.keys(FIELDS)) {
      $(ctl).addEventListener("click", () => {
        const box = $(ctl);
        const lines = box.value.trim() ? [`입력된 내용 : ${box.value}`] : [];
        if (box.style.backgroundColor === BAD) {
          if (ctl === "txt_isbn" && box.value.trim() !== $("txt_ISBNSearch").value.trim()) {
            lines.push("", " 검색한 ISBN과 입력된 ISBN이 일치하지 않습니다.",
              `검색한 ISBN : ${$("txt_ISBNSearch").value}`, `입력된 ISBN : ${box.value}`);
          } else {
            lines.push("", " 숫자형태로 입력해주세요.");
          }
        }
        if (lines.length) $("txt_Check").value = lines.join("\n");
      });
    }

    // btn_GetBookInfo_Click(): the fields become a new record in 도서관리
    function take() {
      const book = Object.fromEntries(Object.entries(FIELDS).map(([ctl, field]) => [field, $(ctl).value.trim()]));
      if (!book.title && !book.isbn) return ctx.msgBox("가져올 도서를 목록에서 선택해주세요.");
      ctx.bus.emit("isbnBookPicked", book);
      ctx.close();
    }

    $("btn_Search").addEventListener("click", search);
    $("txt_ISBNSearch").addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); search(); }
    });
    // txt_ISBNSearch_Enter / _Click select the text
    $("txt_ISBNSearch").addEventListener("focus", () => $("txt_ISBNSearch").select());
    $("btn_CheckData").addEventListener("click", check);
    $("btn_GetBookInfo").addEventListener("click", take);
    $("btn_Close").addEventListener("click", () => ctx.close());

    // What 도서관리 searched, with its results
    const start = {};
    ctx.bus.emit("isbnSearchStart", start);
    if (start.query) $("txt_ISBNSearch").value = start.query;
    if (start.found) show(start.found);
  },
};
