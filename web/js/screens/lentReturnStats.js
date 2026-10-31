// 대출/반납 통계 (Lent_ReturnStats.cs). 조회 picks one of ten result grids from the
// options, as btn_stats_Click() does, and fills it from the lending history.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.Lent_ReturnStats = {
  server: true,
  // Every grid sits at (12, 201) and fills the rest of the form (width - 27, height - 210)
  arrange({ root, nodes, render }) {
    for (const n of nodes) {
      const el = render(n);
      if (n.type === "list") el.style.cssText = "left:12px;top:201px;right:15px;bottom:9px";
      root.append(el);
    }
  },
  columns: { totallist: "equal", monthlist: "equal", bookTotallist: "equal", bookMonthlist: "equal",
    bookDatelist: "equal", userTotallist: "equal", userMonthlist: "equal", userDatelist: "equal",
    detaillist: "equal", numbercnt_Grid: "equal" },

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const GRIDS = ["totallist", "monthlist", "bookTotallist", "bookMonthlist", "bookDatelist",
      "userTotallist", "userMonthlist", "userDatelist", "detaillist", "numbercnt_Grid"];
    const fill = (name, values) => $(name).replaceChildren(...values.map(v =>
      Object.assign(document.createElement("option"), { value: v, textContent: v })));

    // LoadSetting()
    const today = lib.today();
    $("dateTimePicker1").value = today;
    $("dateTimePicker2").value = today;
    $("radio_Lent").checked = true;
    $("radio_summary").checked = true;
    let visible = "totallist";
    const showGrid = id => { GRIDS.forEach(g => { ctx.box(g).hidden = g !== id; }); visible = id; };
    showGrid("totallist");

    // SwitchParam(): 도서별/회원별 show a keyword box; 연체현황 disables the 대출/반납 choice
    const KEYWORD = ["label_text", "label_text2", "label_text3", "txt_keyword", "btn_search", "combo_index2"];
    function switchParam() {
      const index = $("combo_index").selectedIndex;
      KEYWORD.forEach(n => { ctx.box(n).hidden = index === 0; });
      if (index === 1) {
        $("btn_search").textContent = "도서검색";
        fill("combo_index2", ["등록번호", "서명"]);
      } else if (index === 2) {
        $("btn_search").textContent = "회원검색";
        fill("combo_index2", ["회원번호", "회원명"]);
      }
      ctx.box("label_text").textContent = "검색어";
      $("combo_lent").disabled = !$("radio_Lent").checked;
    }
    ["radio_Lent", "radio_delay"].forEach(n => $(n).addEventListener("change", switchParam));
    $("combo_index").addEventListener("change", switchParam);
    switchParam();

    // ---- the numbers --------------------------------------------------------

    async function events() {
      const from = $("dateTimePicker1").value, to = $("dateTimePicker2").value;
      const kinds = !$("radio_Lent").checked ? ["연체"]
        : [["대출", "반납"], ["대출"], ["반납"]][$("combo_lent").selectedIndex];
      // The server reads only the chosen dates; the sample library returns everything
      let list = (await lib.history(from, to)).filter(h => h.date >= from && h.date <= to && kinds.includes(h.kind));
      // 도서별 / 회원별 keyword: several values separated by ';'
      const index = $("combo_index").selectedIndex;
      const words = $("txt_keyword").value.split(";").map(w => w.trim().toLowerCase()).filter(Boolean);
      if (index && words.length) {
        const by = $("combo_index2").value;
        const field = { 등록번호: "barcode", 서명: "title", 회원번호: "userId", 회원명: "userName" }[by];
        const exact = by === "등록번호" || by === "회원번호";
        list = list.filter(h => words.some(w => (exact ? h[field].toLowerCase() === w : h[field].toLowerCase().includes(w))));
      }
      return { list, kinds };
    }
    const period = d => ["", d.slice(0, 7), d][$("combo_period").selectedIndex];
    const kdc = h => `kdc${Math.min(9, parseInt(h.category, 10) / 100 | 0)}`;
    const groupBy = (list, keyFn) => {
      const m = new Map();
      for (const h of list) { const k = keyFn(h); if (!m.has(k)) m.set(k, []); m.get(k).push(h); }
      return m;
    };
    const kdcRow = (state, items, extra = {}) => {
      const row = { state, ...extra, sum: items.length };
      for (let i = 0; i <= 9; i++) row[`kdc${i}`] = 0;
      items.forEach(h => { row[kdc(h)]++; });
      return row;
    };
    const counts = items => ({
      lent: items.filter(h => h.kind === "대출" || h.kind === "연체").length,
      returned: items.filter(h => h.kind === "반납").length,
    });
    // Group rows that start each month in the 월별 lists
    const monthHeader = month => ({ barcode: `[${month}]`, userId: `[${month}]`, header: true });

    async function stats() {
      if ($("dateTimePicker1").value > $("dateTimePicker2").value) return ctx.msgBox("조회기간 설정이 잘못되었습니다.");
      const { list, kinds } = await events();
      const sorted = [...list].sort((a, b) => a.date.localeCompare(b.date));
      const index = $("combo_index").selectedIndex;
      const p = $("combo_period").selectedIndex;
      let grid, rows;

      if (!$("radio_summary").checked) {
        grid = "detaillist";
        rows = sorted.map((h, i) => ({ no: i + 1, date: h.date, userId: h.userId, userName: h.userName,
          barcode: h.barcode, title: h.title, category: h.category, state: h.kind }));
      } else if ($("combo_view").selectedIndex !== 0) {
        // SearchSumNumber(): distinct members or books per period
        grid = "numbercnt_Grid";
        const field = $("combo_view").selectedIndex === 1 ? "userId" : "barcode";
        rows = [...groupBy(sorted, h => period(h.date) || "전체")].map(([d, items]) =>
          ({ date: d, userCount: new Set(items.map(h => h[field])).size }));
      } else if (index === 0) {
        if (p === 0) {
          grid = "totallist";
          rows = kinds.map(k => kdcRow(k, list.filter(h => h.kind === k)));
        } else {
          grid = "monthlist";
          rows = [...groupBy(sorted, h => period(h.date))].flatMap(([d, items]) =>
            kinds.map(k => kdcRow(k, items.filter(h => h.kind === k), { date: d })));
        }
      } else {
        const byBook = index === 1;
        const keyOf = h => (byBook ? h.barcode : h.userId);
        const describe = (items) => (byBook
          ? { barcode: items[0].barcode, title: items[0].title, category: items[0].category }
          : { userId: items[0].userId, userName: items[0].userName, userGrade: items[0].userGrade });
        if (p === 0) {
          grid = byBook ? "bookTotallist" : "userTotallist";
          rows = [...groupBy(sorted, keyOf)].map(([, items]) => ({ ...describe(items), ...counts(items) }));
        } else if (p === 1) {
          grid = byBook ? "bookMonthlist" : "userMonthlist";
          rows = [...groupBy(sorted, h => period(h.date))].flatMap(([month, items]) => [monthHeader(month),
            ...[...groupBy(items, keyOf)].map(([, its]) => ({ ...describe(its), ...counts(its) }))]);
        } else if (byBook) {
          grid = "bookDatelist";
          rows = sorted.map((h, i) => ({ no: i + 1, date: h.date, barcode: h.barcode, title: h.title, category: h.category, state: h.kind }));
        } else {
          grid = "userDatelist";
          rows = [...groupBy(sorted, h => `${h.date}|${h.userId}`)].map(([, items], i) =>
            ({ no: i + 1, date: items[0].date, userId: items[0].userId, userName: items[0].userName, ...counts(items) }));
        }
      }
      showGrid(grid);
      ctx.list(grid).setRows(rows);
      ctx.list(grid).rowClass(r => (r.header ? "row-group" : ""));
    }

    // 출력: print the visible grid
    function print() {
      const table = ctx.box(visible).querySelector("table");
      const w = window.open("", "_blank");
      if (!w) return ctx.msgBox("팝업이 차단되어 출력할 수 없습니다.");
      w.document.write(`<!doctype html><meta charset="utf-8"><title>대출/반납 현황</title>
        <style>body{font:12px "Malgun Gothic",sans-serif}table{border-collapse:collapse;width:100%}
        th,td{border:1px solid #999;padding:3px 6px}th{background:#eee}td.num{text-align:right}</style>
        <h3>대출/반납 현황 ${$("dateTimePicker1").value} ~ ${$("dateTimePicker2").value}</h3>${table.outerHTML}`);
      w.document.close();
      w.focus();
      w.print();
    }

    $("btn_stats").addEventListener("click", stats);
    $("btn_save").addEventListener("click", () => ctx.list(visible).exportCsv());
    $("btn_print").addEventListener("click", print);
    $("btn_search").addEventListener("click", () => ctx.openDialog($("combo_index").selectedIndex === 1 ? "SearchBooks" : "UserSearch"));
  },
};
