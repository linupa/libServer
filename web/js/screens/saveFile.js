// 파일로 저장 (SaveFileProcess.cs, CRLFDlg.cs): the books checked in 도서관리, as a MARC file
// (Marc 파일 저장, which first asks about line breaks) or a table of their fields (엑셀파일 저장).
// Each saved book is unchecked in the list, as CLIB does.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
(function () {
  function download(blob, name) {
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: name });
    document.body.append(a);
    a.click();
    a.remove();
    // Revoked at once, Chrome can cancel the download before it has read the blob
    setTimeout(() => URL.revokeObjectURL(a.href), 60000);
  }
  // 도서관리's checked rows: { rows, done(savedRows) }
  function checkedBooks(ctx) {
    const out = {};
    ctx.bus.emit("collectBookRows", out);
    return out.rows && out.rows.length ? out : null;
  }
  const today = () => { const d = new Date(); return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`; };

  // MARC 파일 저장: 일반, or a CRLF after each record (줄바꿈 문자 포함)
  window.CLIB_LOGIC.CRLFDlg = {
    server: true,
    ownClose: true, // ControlBox = false; 확인 and 취소 close it

    init(ctx) {
      const lib = ctx.library;
      const $ = ctx.input;
      $("button2").addEventListener("click", () => ctx.close());
      $("button1").addEventListener("click", async () => {
        const crlf = $("radioButton2").checked;
        ctx.close();
        const books = checkedBooks(ctx);
        if (!books) return ctx.msgBox("선택된 도서가 없습니다.");
        // SaveMarcFileThFn(): each record ends with the record terminator
        const { blob, count } = await lib.marcFile(books.rows.map(r => ({
          record: r.rec, original: r.original, saved: r.status === "saved" })), crlf);
        download(blob, `도서목록_${today()}.mrc`);
        books.done(books.rows);
        await ctx.msgBox(`총 ${count}개 마크 저장`);
      });
    },
  };

  // 엑셀파일 저장: CHEADER's columns, one row per checked book. Saved as CSV (UTF-8 with a
  // BOM, which Excel opens), like the other 파일저장 buttons of this port.
  const HEADER = ["번호", "등록번호", "서명", "저자", "서명권차", "총서명", "저자기호", "별치기호", "분류기호", "청구권차",
    "복본기호", "ISBN", "딸림자료", "출판사", "출판년도", "발행지", "페이지", "크기", "가격", "등록일"];
  // CDATANAME: BARCODE … PRICE, as GetBookInfo() reads them from the editor
  const FIELDS = ["barcode", "title", "author", "volume", "seriesTitle", "authorCode", "exCate", "category",
    "claimVolume", "copy", "isbn", "attach", "publisher", "year", "pubPlace", "pages", "size", "price"];

  window.CLIB_LOGIC.SaveFileProcess = {
    server: true,
    ownClose: true, // borderless progress window; 취소 stops it

    init(ctx) {
      const $ = ctx.input;
      let running = true;
      $("btn_cancle").addEventListener("click", () => { running = false; ctx.close(); });

      (async () => {
        const books = checkedBooks(ctx);
        if (!books) {
          ctx.close();
          return ctx.msgBox("선택된 도서가 없습니다.");
        }
        const bar = $("progressBar1");
        bar.max = books.rows.length;
        const esc = v => `"${String(v ?? "").trim().replace(/"/g, '""')}"`;
        const lines = [HEADER.map(esc).join(",")];
        const saved = [];
        for (const r of books.rows) {
          if (!running) return;
          lines.push([saved.length + 1, ...FIELDS.map(f => r.rec[f]), r.regDate].map(esc).join(","));
          saved.push(r);
          bar.value = saved.length;
          if (saved.length % 50 === 0) await new Promise(requestAnimationFrame);
        }
        download(new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" }), `도서목록_${today()}.csv`);
        books.done(saved);
        ctx.close();
        await ctx.msgBox(`총 ${saved.length}개 도서 저장`);
      })();
    },
  };
})();
