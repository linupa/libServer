// 도서보유현황 (BookStats.cs) and 이용자현황 (UserStats.cs): 조회 counts books or members per
// group on the left; clicking a row lists them on the right (TotalProgerssDlg's detail loaders).
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
(function () {
  // InsertTotalData(): count / 전체 * 100, cut (not rounded) to two decimals, as text + " %"
  function ratio(count, total) {
    const text = String(count / total * 100);
    if (!Number.isFinite(count / total)) return "0 %";
    const [whole, frac] = text.split(".");
    return `${frac ? `${whole}.${frac.slice(0, 2)}` : whole} %`;
  }

  // *_SizeChanged(): the totals take 35% of the width and 60% of (height - 80); the details
  // start where the totals end (keeping the designer's gap) and fill the rest
  function arrange(gap) {
    return ({ root, nodes, render }) => {
      for (const n of nodes) {
        const el = render(n);
        if (n.id === "totallist") el.style.cssText = `left:${n.x}px;top:${n.y}px;width:35%;height:calc((100% - 80px) * 0.6)`;
        if (n.id === "detaillist") el.style.cssText = `left:calc(35% + ${gap}px);top:${n.y}px;right:10px;bottom:15px`;
        // its right edge on the totals' right edge (the list starts 493px left of it in the designer)
        if (n.id === "btn_savetotal") Object.assign(el.style, { left: `calc(${n.x + n.w - 493}px + 35% - ${n.w}px)` });
        if (n.id === "btn_savedetail") Object.assign(el.style, { left: "auto", right: "10px" });
        if (n.id === "label3") Object.assign(el.style, { left: `calc(35% + ${gap + 10}px)` });
        root.append(el);
      }
    };
  }

  function statsScreen({ headers, key, loadTotals, loadDetail }) {
    return (ctx) => {
      const lib = ctx.library;
      const $ = ctx.input;
      const total = ctx.list("totallist");
      const detail = ctx.list("detaillist");
      const head = ctx.box("totallist").querySelector("thead th");
      let searched = null;  // the grouping of the totals on screen

      async function search() {
        const by = $("comboBox1").selectedIndex;
        const result = await loadTotals(lib, by);
        if (result.error) return ctx.msgBox(result.error);
        // The first column is named after the grouping
        if (head) head.textContent = headers[by];
        const all = result.rows[0] ? result.rows[0].count : 0;
        total.setRows(result.rows.map((r, i) => ({ [key]: r.name, count: r.count, ratio: ratio(r.count, all), row: i })));
        detail.setRows([]);
        searched = by;
      }

      total.onRowClick(async r => {
        if (searched === null) return;
        document.body.style.cursor = "wait";
        try {
          const result = await loadDetail(lib, searched, r[key], r.row);
          if (result.error) return ctx.msgBox(result.error);
          detail.setRows(result.rows);
        } finally {
          document.body.style.cursor = "";
        }
      });
      $("btn_search").addEventListener("click", search);
      $("btn_savetotal").addEventListener("click", () => total.exportCsv());
      $("btn_savedetail").addEventListener("click", () => detail.exportCsv());
      $("comboBox1").selectedIndex = 0;
    };
  }

  const BOOK_HEADERS = ["도서상태", "도서분류", "별치기호", "소장위치", "반입구분"];
  const bookInit = statsScreen({
    headers: BOOK_HEADERS, key: "bookState",
    loadTotals: async (lib, by) => ({ rows: await lib.bookStats(by) }),
    loadDetail: async (lib, by, name, row) => ({ rows: await lib.bookStatsDetail(by, name, row) }),
  });
  window.CLIB_LOGIC.BookStats = {
    server: true,
    arrange: arrange(32),
    columns: { totallist: "equal" },
    // comboBox2 (LoadIndex's list of groups) is hidden in CLIB and 조회 never reads it
    init(ctx) { bookInit(ctx); },
  };

  const userInit = statsScreen({
    headers: ["회원등급", "회원상태"], key: "userGrade",
    loadTotals: (lib, by) => lib.userStats(by),
    loadDetail: (lib, by, name) => lib.userStatsDetail(by, name),
  });
  window.CLIB_LOGIC.UserStats = {
    server: true,
    arrange: arrange(32),
    columns: { totallist: "equal" },
    init(ctx) { userInit(ctx); },
  };
})();
