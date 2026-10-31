// 이용현황 (LentStats.cs): current loans, reservations, or attachments still out.
// The top of the SplitContainer has the search; the bottom shows LentFrm, ReservationFrm
// or AttachFrm's grid, picked with the radio buttons.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.LentStats = {
  server: true,
  // FixedPanel = Panel1 (92px); Panel2 fills the rest
  arrange({ root, nodes, render, controls }) {
    for (const n of nodes) {
      const el = render(n);
      el.style.cssText = "left:0;top:0;right:0;height:92px";
      root.append(el);
    }
    const bottom = Object.assign(document.createElement("div"), { className: "ctl panel lent-stats-grid" });
    bottom.style.cssText = "left:0;top:96px;right:0;bottom:0";
    root.append(bottom);
    controls.__grid = bottom;
  },

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const host = ctx.el("__grid");
    const MODES = {
      radio_lent: { screen: "LentFrm", rows: lentRows },
      radio_reserve: { screen: "ReservationFrm", rows: reserveRows },
      radio_attach: { screen: "AttachFrm", rows: attachRows },
    };
    let mode = "radio_lent";
    let grid;

    // combo_index_SelectedIndexChanged(): 도서검색 searches books, 회원검색 members
    const fill = (name, values) => $(name).replaceChildren(...values.map(v =>
      Object.assign(document.createElement("option"), { value: v, textContent: v })));
    function syncIndex() {
      fill("combo_index2", $("combo_index").value === "도서검색" ? ["등록번호", "서명"] : ["회원번호", "회원명"]);
    }
    $("combo_index").value = "회원검색";
    syncIndex();
    $("combo_index").addEventListener("change", syncIndex);
    $("radio_lent").checked = true;

    const title = b => (b.volume ? `${b.title}. ${b.volume}` : `${b.title}.`);
    async function lentRows() {
      return (await lib.allLoans()).sort((a, b) => a.lentDate.localeCompare(b.lentDate)).map(l => ({
        bookState: l.state === "연체중" ? "연체" : "대출", barcode: l.barcode, title: title(l.book), author: l.book.author,
        borrower: l.user.userName, userId: l.userId, phone: l.user.phone, address: l.user.address,
        lendDate: l.lentDate, dueDate: l.dueDate, late: l.state === "연체중" }));
    }
    async function reserveRows() {
      return (await lib.allReservations()).map(r => ({
        barcode: r.book.barcode, title: title(r.book), author: r.book.author, reserver: r.user.userName,
        userId: r.user.userId, phone: r.user.phone, address: r.user.address, reserveDate: "",
        reserveOrder: r.position, reserveExpire: r.holdUntil }));
    }
    async function attachRows() {
      return (await lib.allLoans()).filter(l => l.withAttach).map(l => ({
        state: "대출", barcode: l.barcode, title: title(l.book), attach: l.book.attach, borrower: l.user.userName,
        userId: l.userId, phone: l.user.phone, address: l.user.address, lendDate: l.lentDate, own: true }));
    }

    async function search() {
      const m = MODES[mode];
      if (!grid || grid.mode !== mode) {
        host.replaceChildren();
        grid = ctx.table(host, m.screen, "LentGrid", { rowNumbers: true });
        grid.mode = mode;
        // LentFrm tints overdue rows Beige; AttachFrm tints the borrower's own attachments Bisque
        grid.rowClass(r => (r.late ? "row-late" : r.own ? "row-attach" : ""));
      }
      const words = $("txt_keyword").value.split(";").map(w => w.trim().toLowerCase()).filter(Boolean);
      const field = { 등록번호: "barcode", 서명: "title", 회원번호: "userId", 회원명: mode === "radio_reserve" ? "reserver" : "borrower" }[$("combo_index2").value];
      const rows = (await m.rows()).filter(r => !words.length || words.some(w => String(r[field]).toLowerCase().includes(w)));
      grid.setRows(rows);
    }

    for (const id of Object.keys(MODES)) {
      $(id).addEventListener("change", () => { mode = id; $("txt_keyword").value = ""; search(); });
    }
    $("btn_search").addEventListener("click", search);
    $("txt_keyword").addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) search(); });
    $("btn_save").addEventListener("click", () => grid.exportCsv());
    $("btn_print").addEventListener("click", () => {
      const w = window.open("", "_blank");
      if (!w) return ctx.msgBox("팝업이 차단되어 출력할 수 없습니다.");
      w.document.write(`<!doctype html><meta charset="utf-8"><title>이용현황</title>
        <style>body{font:11px "Malgun Gothic",sans-serif}table{border-collapse:collapse;width:100%}
        th,td{border:1px solid #999;padding:2px 4px}th{background:#eee}</style>${host.querySelector("table").outerHTML}`);
      w.document.close();
      w.print();
    });
    search();
  },
};
