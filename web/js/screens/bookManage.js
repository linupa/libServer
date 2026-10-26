// 도서관리 (BookManage.cs). A work list of books on the left and the record editor on
// the right. Edits are kept in the work list until 저장; row colours follow the legend
// (white = saved, bisque = 필수항목 누락, light grey = not saved).
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.BookManage = {
  server: true,
  // BookManage_SizeChanged(): the editor column keeps its width on the right and the
  // book list takes the rest; 고정필드 (panel1, 165px) pushes the editor down.
  arrange({ root, nodes, render, controls }) {
    const div = cls => Object.assign(document.createElement("div"), { className: cls });
    const left = div("bm-left");
    const right = div("bm-right");
    root.append(left, right);
    const RIGHT_X = 449; // tabControl1.Location.X: the column's left edge in the designer
    const LIST_RIGHT = 429; // booklist right edge, which the 새작업/일괄저장/일괄삭제 buttons line up with
    for (const n of nodes) {
      const el = render(n);
      if (n.id === "panel6") multiLineLoad(el, controls);
      if (n.x >= RIGHT_X) {
        el.style.left = `${n.x - RIGHT_X}px`;
        right.append(el);
      } else if (["btn_new", "btn_batchSave", "btn_batchDel"].includes(n.id)) {
        el.style.left = "auto";
        el.style.right = `${LIST_RIGHT - (n.x + n.w)}px`;
        left.append(el);
      } else if (n.id === "booklist") {
        el.style.cssText = `left:${n.x}px;top:${n.y}px;right:0;bottom:54px`;
        left.append(el);
      } else if (n.id === "index_panel") {
        el.style.top = "auto";
        el.style.bottom = "5px";
        left.append(el);
      } else {
        left.append(el);
      }
    }
    // Vertical stack from BookManage_SizeChanged()
    right.relayout = showFixed => {
      const panel1 = controls["panel1:box"];
      panel1.hidden = !showFixed;
      panel1.style.height = "165px";
      const place = (id, top) => { controls[`${id}:box`].style.top = `${top}px`; return top + controls[`${id}:box`].offsetHeight; };
      let y = 10 + (showFixed ? 165 : 0);
      controls["btn_detailView:box"].style.top = `${y}px`;
      y += 20 + 5;
      y = place("panel_button", y) + 5;
      y = place("panel6", y) + 5;
      place("tabControl1", y);
    };
    controls.__right = right;

    // 저장된 도서 불러오기 takes several 등록번호, one per line (CLIB's box is one line):
    // the box becomes a three-line text area and the pink panel grows to fit it
    function multiLineLoad(panel, controls) {
      const LINES = 3, LINE = 17;
      const input = controls.txt_LoadBarcode;
      const area = Object.assign(document.createElement("textarea"), {
        id: input.id, className: `${input.className} load-barcodes`, rows: LINES, spellcheck: false,
        placeholder: "등록번호 (한 줄에 하나씩)",
      });
      area.setAttribute("autocomplete", "off");
      area.style.cssText = input.style.cssText;
      area.style.height = `${LINES * LINE + 6}px`;
      input.replaceWith(area);
      controls.txt_LoadBarcode = controls["txt_LoadBarcode:box"] = area;
      panel.style.height = `${parseInt(panel.style.height, 10) + (LINES - 1) * LINE + 2}px`;
    }
  },

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("booklist");
    const authorCode = window.CLIB.authorCode;

    // Editor control -> record field
    const FIELDS = {
      txt_isbn: "isbn", txt_totalname: "seriesTitle", txt_bookname: "title", txt_booknamenum: "volume",
      txt_author: "author", txt_location: "pubPlace", txt_year: "year", txt_publish: "publisher",
      txt_page: "pages", txt_size: "size", txt_price: "price", txt_attach: "attach",
      combo_bookLocation: "location", combo_bookin: "bookIn", combo_bookstate: "state", txt_UID: "uid",
      txt_exCate: "exCate", txt_category: "category", txt_authorcode: "authorCode",
      txt_booknum: "claimVolume", txt_copy: "copy", txt_barcode: "barcode",
    };
    // Required fields in CLIB's checking order, with its messages
    const REQUIRED = [
      ["txt_bookname", "도서명을 입력해주세요"], ["txt_author", "저자명을 입력해주세요"],
      ["txt_category", "분류기호를 입력해주세요"], ["txt_authorcode", "저자기호를 입력해주세요"],
      ["txt_barcode", "등록번호를 입력해주세요"],
    ];

    const fillCombo = (name, values) => {
      $(name).replaceChildren(...values.map(v => Object.assign(document.createElement("option"), { value: v, textContent: v })));
    };
    fillCombo("combo_bookLocation", lib.codes.location);
    fillCombo("combo_bookin", lib.codes.bookIn);
    fillCombo("combo_bookstate", lib.codes.state);

    let rows = [];
    let current = null; // row being edited; null for a new record
    let showFixed = false;
    const right = ctx.el("__right");
    requestAnimationFrame(() => right.relayout(showFixed));

    const blank = () => ({ location: lib.codes.location[0], bookIn: lib.codes.bookIn[0], state: lib.codes.state[0] });
    const readForm = () => Object.fromEntries(Object.entries(FIELDS).map(([ctl, f]) => [f, $(ctl).value.trim()]));
    function writeForm(rec) {
      for (const [ctl, f] of Object.entries(FIELDS)) $(ctl).value = rec[f] ?? "";
      $("txt_isbnSearch").value = "";
      // A record read from CLIB's database shows its real MARC until it is edited
      if (rec.marcText) $("txt_marc").value = rec.marcText;
      else refreshMarc();
    }
    const missingField = rec => REQUIRED.find(([ctl]) => !rec[FIELDS[ctl]]);

    function toRow(rec, status, original) {
      return { checked: false, barcode: rec.barcode, uid: rec.uid, bookState: rec.state, title: rec.title,
        author: rec.author, publisher: rec.publisher, category: rec.category, authorCode: rec.authorCode,
        volume: rec.volume, copy: rec.copy, exCate: rec.exCate, isbn: rec.isbn, location: rec.location,
        bookIn: rec.bookIn, regDate: rec.regDate || "", modDate: rec.modDate || "",
        rec, status, original };
    }
    function redraw(select) {
      rows.forEach((r, i) => { r.no = i + 1; });
      list.setRows(rows);
      if (select) list.select(select);
    }
    list.rowClass(r => (r.status === "missing" ? "row-missing" : r.status === "unsaved" ? "row-unsaved" : ""));
    list.onRowClick(r => { current = r; writeForm(r.rec); });

    // Editing keeps the record in its row, marked as not saved
    function edited() {
      if (!current) return;
      const rec = { ...current.rec, ...readForm(), marcText: "" };
      const keep = { checked: current.checked, no: current.no };
      Object.assign(current, toRow(rec, "unsaved", current.original), keep);
      list.refresh();
    }
    for (const ctl of Object.keys(FIELDS)) {
      $(ctl).addEventListener($(ctl).tagName === "SELECT" ? "change" : "input", () => { edited(); refreshMarc(); });
    }

    function addRows(books) {
      for (const b of books) {
        const row = toRow(b, "saved", b.barcode);
        const i = rows.findIndex(r => r.barcode === b.barcode);
        if (i >= 0) rows[i] = row; else rows.push(row);
      }
      redraw();
    }

    // ---- 이전 / 다음 / 신규 / 저장 / 삭제 --------------------------------

    function move(step) {
      if (!rows.length) return;
      const i = current ? rows.indexOf(current) : -1;
      const next = rows[Math.min(rows.length - 1, Math.max(0, i + step))];
      current = next;
      list.select(next);
      writeForm(next.rec);
    }

    function newRecord() {
      current = null;
      list.select(null);
      writeForm(blank());
      $("txt_isbn").focus();
    }

    async function save() {
      const rec = { ...(current ? current.rec : {}), ...readForm() };
      const missing = missingField(rec);
      if (missing) {
        if (current) { current.status = "missing"; list.refresh(); }
        await ctx.msgBox(missing[1], "필수항목 누락");
        return $(missing[0]).focus();
      }
      const isNew = !current || !current.original;
      if (isNew ? !await ctx.confirm("도서정보를 최종저장하시겠습니까?", "서지저장")
                : !await ctx.confirm("도서정보를 수정하시겠습니까?", "서지수정")) return;
      const answers = {};
      let result = await lib.saveBook(rec, { originalBarcode: current && current.original, answers });
      while (result.confirm) {
        // The sample library's only question is 등록번호 중복
        answers[result.ask || "overwrite"] = await ctx.confirm(result.confirm, result.title);
        if (!answers[result.ask || "overwrite"]) return;
        result = await lib.saveBook(rec, { originalBarcode: current && current.original, overwrite: answers.overwrite, answers });
      }
      if (result.cancelled) return;
      if (result.error) return ctx.msgBox(result.error, result.title);
      const row = toRow(result.book, "saved", result.book.barcode);
      const dup = rows.find(r => r !== current && r.barcode === row.barcode);
      if (dup) rows.splice(rows.indexOf(dup), 1);
      if (current) rows[rows.indexOf(current)] = Object.assign(row, { checked: current.checked });
      else rows.push(row);
      current = row;
      redraw(row);
      writeForm(row.rec);
    }

    async function remove() {
      if (!current) return newRecord();
      if (!await ctx.confirm("선택한 도서를 삭제하시겠습니까?", "정보삭제")) return;
      if (current.original) {
        if (!await ctx.confirm("데이터베이스에서 완전 삭제하시겠습니까?\n삭제된 도서의 대출기록은 조회되지 않습니다.", "정보삭제")) return;
        const result = await lib.deleteBook(current.original);
        if (result.error) return ctx.msgBox(result.error);
      }
      rows.splice(rows.indexOf(current), 1);
      redraw();
      newRecord();
    }

    // ---- top buttons --------------------------------------------------------

    function toggleAll() {
      const on = !rows.every(r => r.checked);
      rows.forEach(r => { r.checked = on; });
      list.refresh();
    }

    async function batchSave() {
      const picked = rows.filter(r => r.checked);
      if (!picked.length) return;
      if (!await ctx.confirm("선택한 도서를 모두 데이터베이스에 저장하시겠습니까?", "일괄저장")) return;
      for (const r of picked) {
        if (missingField(r.rec)) { r.status = "missing"; continue; }
        const result = await lib.saveBook(r.rec, { originalBarcode: r.original, overwrite: true });
        if (result.ok) Object.assign(r, toRow(result.book, "saved", result.book.barcode), { checked: false });
      }
      redraw(current);
      await ctx.msgBox("완료");
    }

    async function batchDelete() {
      const picked = rows.filter(r => r.checked);
      if (!picked.length) return;
      if (!await ctx.confirm("선택한 도서를 데이터베이스에서 완전 삭제하시겠습니까?", "일괄삭제")) return;
      const errors = [];
      for (const r of picked) {
        const result = r.original ? await lib.deleteBook(r.original) : { ok: true };
        if (result.error) errors.push(`${r.barcode} : ${result.error.split("\n")[0]}`);
        else rows.splice(rows.indexOf(r), 1);
      }
      if (!rows.includes(current)) newRecord();
      redraw(current);
      if (errors.length) await ctx.msgBox(errors.join("\n"));
    }

    async function newWork() {
      if (rows.some(r => r.status !== "saved") &&
          !await ctx.confirm("저장되지 않은 도서정보는 복구되지 않습니다.\n계속 하시겠습니까?", "새작업")) return;
      rows = [];
      redraw();
      newRecord();
    }

    // ---- 저장된 도서 불러오기 (pink panel) and 도서 불러오기 dialog ----------

    // Every 등록번호 in the box (one per line; commas and spaces separate them too). Those not
    // found stay in the box to be corrected; one 등록번호 gives CLIB's own messages.
    async function loadByBarcode() {
      const box = $("txt_LoadBarcode");
      const wanted = [...new Set(box.value.split(/[\s,;]+/).map(b => b.trim()).filter(Boolean))];
      if (!wanted.length) return ctx.msgBox("조회할 등록번호를 입력해주세요.");
      const books = await lib.findBooks(wanted, { full: true });
      const byCode = new Map(books.map(b => [b.barcode.toUpperCase(), b]));
      // A short number (HK915) is only found one at a time, through CLIB's padding
      const missing = [];
      for (const code of wanted.filter(w => !byCode.has(w.toUpperCase()))) {
        const book = await lib.findBook(code, { full: true });
        if (book) byCode.set(code.toUpperCase(), book); else missing.push(code);
      }
      const found = [...new Map([...byCode.values()].map(b => [b.barcode, b])).values()];
      const already = found.filter(b => rows.some(r => r.barcode === b.barcode));
      addRows(found.filter(b => !already.includes(b)));
      const last = found.length ? rows.find(r => r.barcode === found[found.length - 1].barcode) : null;
      if (last) { current = last; list.select(last); writeForm(last.rec); }
      box.value = missing.join("\n");
      if (wanted.length === 1) {
        if (missing.length) await ctx.msgBox("해당하는 도서가 없습니다.");
        else if (already.length) await ctx.msgBox("이미 목록에 존재하는 도서입니다.");
      } else if (missing.length || already.length) {
        await ctx.msgBox([`불러온 도서 : ${found.length - already.length}권`,
          already.length ? `이미 목록에 있는 도서 : ${already.map(b => b.barcode).join(", ")}` : "",
          missing.length ? `해당하는 도서가 없습니다 : ${missing.join(", ")}` : ""].filter(Boolean).join("\n"));
      }
      box.focus();
      box.select();
    }

    // 청구기호 출력 asks for the checked books (CheckClaim())
    const offCollect = ctx.bus.on("collectBooks", out => {
      if (!ctx.box("booklist").isConnected) return offCollect();
      out.total = rows.length;
      out.books = rows.filter(r => r.checked).map(r => r.rec);
    });
    // 파일로 저장 asks for the checked rows and unchecks the ones it saved (BookListCheck(false))
    const offFile = ctx.bus.on("collectBookRows", out => {
      if (!ctx.box("booklist").isConnected) return offFile();
      out.rows = rows.filter(r => r.checked);
      out.done = saved => { saved.forEach(r => { r.checked = false; }); list.refresh(); };
    });

    const off = ctx.bus.on("loadBooks", async barcodes => {
      // The view is rebuilt when you leave and come back; drop listeners of old copies
      if (!ctx.box("booklist").isConnected) return off();
      const books = await lib.findBooks(barcodes, { full: true });
      const dups = books.filter(b => rows.some(r => r.barcode === b.barcode));
      const keep = dups.length && !await ctx.confirm("같은 등록번호의 도서가 이미 화면상에 존재합니다.\n새로 불러오시겠습니까?", "중복도서")
        ? books.filter(b => !dups.includes(b)) : books;
      addRows(keep);
    });

    // ---- 일반용 helpers -------------------------------------------------------

    function makeAuthorCode() {
      const result = authorCode.check($("txt_author").value, $("txt_bookname").value, lib.settings.book.authorCode);
      if (result.error) return ctx.msgBox(result.error);
      $("txt_authorcode").value = result.code;
      edited();
      refreshMarc();
    }

    // ---- 전문가용: MARC text --------------------------------------------------

    // A KORMARC-style view of the record. ▼ starts a subfield, ▲ ends a field, ↔ ends the record.
    function marcText(r) {
      const f = (tag, ind, subs) => {
        const body = subs.filter(([, v]) => v).map(([c, v]) => `▼${c}${v}`).join("");
        return body ? `${tag}\t${ind}\t${body}▲` : null;
      };
      return [
        "00000nam  2200000 k 4500▲",
        "008\t\t" + `${(lib.today() || "").replace(/-/g, "").slice(2)}s${(r.year || "    ").padEnd(4)}    ulk           000  kor▲`,
        f("020", "  ", [["a", r.isbn], ["c", r.price && `\\${r.price}`]]),
        f("049", "  ", [["l", r.barcode], ["f", r.exCate]]),
        f("056", "  ", [["a", r.category], ["2", r.category && "6"]]),
        f("090", "  ", [["a", r.category], ["b", r.authorCode]]),
        f("245", "00", [["a", r.title], ["n", r.volume], ["d", r.author]]),
        f("260", "  ", [["a", r.pubPlace], ["b", r.publisher], ["c", r.year]]),
        f("300", "  ", [["a", r.pages], ["c", r.size], ["e", r.attach]]),
        f("490", "00", [["a", r.seriesTitle]]),
        f("950", "0 ", [["b", r.price && `\\${r.price}`]]),
      ].filter(Boolean).join("\n") + "↔";
    }
    function refreshMarc() { $("txt_marc").value = marcText(readForm()); }

    const marc = $("txt_marc");
    const lineAt = pos => marc.value.slice(0, pos).split("\n").length - 1;
    function insertSubfield() { // F5
      const line = lineAt(marc.selectionStart);
      const tag = parseInt(marc.value.split("\n")[line], 10);
      if (line <= 1 || !(tag >= 10)) return;
      marc.setRangeText("▼", marc.selectionStart, marc.selectionEnd, "end");
      marc.focus();
    }
    function endField() { // F6
      const lines = marc.value.split("\n");
      const line = lineAt(marc.selectionStart);
      if (line <= 1 || lines[line].endsWith("▲")) return;
      const pos = marc.selectionStart;
      lines[line] += "▲";
      marc.value = lines.join("\n");
      marc.setSelectionRange(pos, pos);
      marc.focus();
    }
    function endRecord() { // F7
      if (marc.value.trim() && !marc.value.endsWith("↔")) marc.value += "↔";
    }
    marc.addEventListener("keydown", e => {
      const fn = { F5: insertSubfield, F6: endField, F7: endRecord }[e.key];
      if (fn) { e.preventDefault(); fn(); }
    });

    // ---- wiring ---------------------------------------------------------------

    const click = (name, fn) => $(name).addEventListener("click", fn);
    click("btn_back", () => move(-1));
    click("btn_foward", () => move(1));
    click("btn_newmarc", newRecord);
    click("btn_save", save);
    click("btn_delete", remove);
    click("btn_AllSel", toggleAll);
    click("btn_new", newWork);
    click("btn_batchSave", batchSave);
    click("btn_batchDel", batchDelete);
    ctx.notPorted("btn_sample");
    click("btn_LoadBook", loadByBarcode);
    // Enter starts a new line (a scanner's Enter too); Ctrl+Enter loads them all
    $("txt_LoadBarcode").addEventListener("keydown", e => {
      if (e.key === "Enter" && e.ctrlKey && !e.isComposing) { e.preventDefault(); loadByBarcode(); }
    });
    // SearchISBN(): a copy already in the library opens 복본검색, otherwise the
    // 국립중앙도서관 results. Both dialogs show sample rows until a backend is connected.
    click("btn_isbnSearch", async () => {
      const isbn = $("txt_isbnSearch").value.trim().replace(/-/g, "");
      if (!isbn) return ctx.msgBox("검색할 ISBN을 입력해주세요.");
      const copies = await lib.searchBooks({ field: "ISBN", keyword: isbn });
      ctx.openDialog(copies.some(b => b.isbn.replace(/-/g, "") === isbn) ? "CopyBookDlg" : "SearchISBNDlg");
    });
    if (!ctx.ported("CopyBookDlg") && !ctx.ported("SearchISBNDlg")) ctx.notPorted("btn_isbnSearch");
    ctx.notPorted("btn_category");
    click("btn_authorcode", makeAuthorCode);
    click("btn_detailView", () => { showFixed = !showFixed; right.relayout(showFixed); });
    click("btn_F5", insertSubfield);
    click("btn_F6", endField);
    click("btn_F7", endRecord);
    ctx.dialogButton("btn_taginfo", "TagDlg");

    $("txt_barcode").title = "샘플 등록번호: EM000001-EM000120";
    $("txt_LoadBarcode").title = `등록번호를 한 줄에 하나씩 입력하고 불러오기(Ctrl+Enter)를 누르세요.${lib.isServer ? "" : "\n샘플 등록번호: EM000001-EM000120"}`;
    newRecord();
  },
};
