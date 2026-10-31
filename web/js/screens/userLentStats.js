// 이용내역 조회 (UserLentStats.cs): one member's 대출 / 반납 / 연체 history, for the whole time
// or a period. Opened from 회원관리 for the 회원번호 in its editor.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.UserLentStats = {
  server: true,
  lists: { statsgrid: { rowNumbers: true } }, // statsgrid_RowPostPaint() numbers the rows

  // A SplitContainer: the search on top (Panel1, 100px), the grid filling Panel2 below it
  arrange({ root, nodes, render, controls }) {
    for (const n of nodes) {
      root.append(render(n));
      if (n.id === "splitContainer1") {
        controls["splitContainer1:box"].style.cssText = "left:0;top:0;right:0;bottom:0";
        controls["statsgrid:box"].style.cssText = "left:0;top:104px;right:0;bottom:0";
      }
    }
  },

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("statsgrid");
    const target = {};
    ctx.bus.emit("userLentStatsTarget", target);
    const userId = target.userId || "";
    ctx.box("label_username").style.width = "auto";
    ctx.box("label_usercode").style.width = "auto";

    const today = lib.today();
    $("dateTimePicker1").value = today;
    $("dateTimePicker2").value = today;
    // radio_period_select_CheckedChanged() / chk_total_Click()
    const syncPeriod = () => ["dateTimePicker1", "dateTimePicker2", "label4"].forEach(n => { ctx.box(n).hidden = !$("radio_period_select").checked; });
    const syncKinds = () => ["chk_lent", "chk_return", "chk_delay"].forEach(n => { $(n).disabled = $("chk_total").checked; });
    $("radio_period_total").addEventListener("change", syncPeriod);
    $("radio_period_select").addEventListener("change", syncPeriod);
    $("chk_total").addEventListener("change", syncKinds);
    syncPeriod();
    syncKinds();

    // LoadUserStats()
    async function search() {
      const kinds = $("chk_total").checked ? null : [["chk_lent", "대출"], ["chk_return", "반납"], ["chk_delay", "연체"]]
        .filter(([n]) => $(n).checked).map(([, k]) => k);
      if (kinds && !kinds.length) return ctx.msgBox("조회기준은 최소 1개 이상 선택해주세요.");
      const found = await lib.userHistory(userId);
      if (!found) return ctx.msgBox(`존재하지 않는 회원번호입니다.\n${userId}`);
      ctx.box("label_usercode").textContent = found.userId;
      // CLIB shows the 회원번호 here too (it reads the wrong column)
      ctx.box("label_username").textContent = found.userName;
      const from = $("dateTimePicker1").value, to = $("dateTimePicker2").value;
      const rows = found.rows.filter(r => (!kinds || kinds.includes(r.state)) &&
        (!$("radio_period_select").checked || (r.date >= from && r.date <= to)));
      list.setRows(rows);
      if (!rows.length) ctx.msgBox("조회된 내용이 없습니다.");
    }

    $("btn_search").addEventListener("click", search);
    $("btn_savefile").addEventListener("click", () => list.exportCsv());
    search();
  },
};
