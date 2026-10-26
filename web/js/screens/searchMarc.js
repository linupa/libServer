// 도서 불러오기 (SearchMarc.cs): search saved books and load the checked ones, or all of
// them (전체 불러오기, in place of CLIB's 전체선택), into 도서관리.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.SearchMarc = {
  server: true,
  ownClose: true, // the form has its own 닫기 button

  arrange({ root, nodes, render, controls }) {
    // 전체 불러오기 sits left of 불러오기
    const all = Object.assign(document.createElement("button"), { type: "button", className: "ctl btn", id: "SearchMarc-btn_loadAll", textContent: "전체 불러오기" });
    all.style.cssText = "right:101px;top:55px;width:95px;height:25px";
    controls.btn_loadAll = all;
    root.append(all);
    for (const n of nodes) {
      const el = render(n);
      // The result grid stretches with the dialog, the 닫기 button stays bottom-right
      if (n.id === "booklist") el.style.cssText = `left:${n.x}px;top:${n.y}px;right:12px;bottom:49px`;
      if (n.id === "btn_exit") Object.assign(el.style, { left: "auto", top: "auto", right: "12px", bottom: "12px" });
      if (["btn_search", "btn_load"].includes(n.id)) Object.assign(el.style, { left: "auto", right: "12px" });
      root.append(el);
    }
  },

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("booklist");
    let rows = [];

    $("radio_normal").checked = true;
    $("combo_index").value = "서명";
    const exCate = $("combo_exCate");
    exCate.replaceChildren(...lib.exCategories().map(v => Object.assign(document.createElement("option"), { value: v, textContent: v })));

    // 일반검색 / 구간검색 enable their own inputs, like CLIB
    function syncMode() {
      const normal = $("radio_normal").checked;
      ["combo_index", "txt_keyword", "date_start", "date_end", "combo_exCate"].forEach(n => { $(n).disabled = !normal; });
      ["txt_Barcode_Start", "txt_Barcode_End"].forEach(n => { $(n).disabled = normal; });
    }
    // combo_index_SelectedIndexChanged(): 등록일 shows a date range, 별치기호 a list
    function syncIndex() {
      const field = $("combo_index").value;
      ctx.box("txt_keyword").hidden = field === "등록일" || field === "별치기호";
      ["date_start", "date_end", "label_date"].forEach(n => { ctx.box(n).hidden = field !== "등록일"; });
      ctx.box("combo_exCate").hidden = field !== "별치기호";
    }
    $("radio_normal").addEventListener("change", syncMode);
    $("radio_barcode").addEventListener("change", syncMode);
    $("combo_index").addEventListener("change", syncIndex);
    syncMode();
    syncIndex();

    async function search() {
      let found;
      if ($("radio_barcode").checked) {
        const start = $("txt_Barcode_Start").value.trim();
        const end = $("txt_Barcode_End").value.trim();
        if (!start && !end) return ctx.msgBox("검색 시작 및 종료 바코드 둘 중 한가지는 반드시 입력해야 합니다.");
        found = await lib.searchBooks({ start, end });
      } else {
        const field = $("combo_index").value;
        found = await lib.searchBooks({
          field,
          keyword: field === "별치기호" ? $("combo_exCate").value : $("txt_keyword").value,
          from: $("date_start").value, to: $("date_end").value,
        });
      }
      rows = found.map((b, i) => ({ checked: false, no: i + 1, barcode: b.barcode, uid: b.uid, bookState: b.state,
        title: b.title, author: b.author, seriesTitle: b.seriesTitle, publisher: b.publisher, category: b.category,
        authorCode: b.authorCode, volume: b.volume, copy: b.copy, exCate: b.exCate, isbn: b.isbn,
        location: b.location, bookIn: b.bookIn, regDate: b.regDate, modDate: b.modDate }));
      list.setRows(rows);
      if (!rows.length) ctx.msgBox("검색 결과가 없습니다.");
    }

    // all: every searched book, checked or not
    async function load(all) {
      const picked = all ? rows : rows.filter(r => r.checked);
      if (!picked.length) return ctx.msgBox(rows.length ? "불러올 도서를 선택해주세요." : "검색된 도서가 없습니다.");
      ctx.bus.emit("loadBooks", picked.map(r => r.barcode));
      ctx.close();
    }

    $("btn_search").addEventListener("click", search);
    ["txt_keyword", "txt_Barcode_Start", "txt_Barcode_End"].forEach(n =>
      $(n).addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) search(); }));
    $("btn_load").addEventListener("click", () => load(false));
    $("btn_loadAll").addEventListener("click", () => load(true));
    $("btn_exit").addEventListener("click", () => ctx.close());
    setTimeout(() => $("txt_keyword").focus());
  },
};
