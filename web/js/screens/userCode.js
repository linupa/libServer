// 등급별 회원번호관리 (UserCodeDlg.cs): the members of one grade. When numbers go by grade
// (회원등급별로 회원번호 사용), those that don't start with the grade's 구분기호 are Bisque;
// 번호변경 gives a member the grade's next number (their loans, reservations and history
// follow), and 전체 재설정 does it for every Bisque row.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.UserCodeDlg = {
  server: true,
  lists: { userlist: { rowNumbers: true } }, // userlist_RowPostPaint() numbers the rows

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("userlist");
    let rows = [];

    $("combo_level").replaceChildren(...lib.grades.map(g =>
      Object.assign(document.createElement("option"), { value: g.grade, textContent: g.grade })));
    const prefix = () => (lib.grades.find(g => g.grade === $("combo_level").value) || {}).prefix || "";
    // Bisque only when numbers go by grade (USERCODE 0)
    const offRule = r => lib.settings.userCodeByGrade && !r.userId.startsWith(prefix());
    list.rowClass(r => (offRule(r) ? "row-bisque" : ""));

    // SearchUser(): 규정에 맞지 않는 번호만 보기 keeps the numbers without the 구분기호
    async function search() {
      const p = prefix();
      rows = (await lib.usersByGrade($("combo_level").value))
        .filter(u => !$("checkBox1").checked || u.userId.slice(0, p.length) !== p)
        .map(u => ({ userGrade: u.userGrade, userId: u.userId, userName: u.userName, changeId: "변경" }));
      list.setRows(rows);
    }

    // ReUserCode(): asks, unless it is part of 전체 재설정
    async function renumber(row, answers = {}) {
      let result = await lib.renumberUser(row.userId, $("combo_level").value, answers);
      while (result.confirm) {
        answers[result.ask] = await ctx.confirm(result.confirm, result.title);
        result = await lib.renumberUser(row.userId, $("combo_level").value, answers);
      }
      if (result.ok) row.userId = result.userId;
      return result;
    }

    list.onButton(async r => {
      const result = await renumber(r);
      if (result.error) return ctx.msgBox(result.error);
      list.refresh();
    });

    $("btn_usercode").addEventListener("click", async () => {
      if (!await ctx.confirm("화면에 표시된 모든 회원번호를 재설정 하시겠습니까?\n※규정에 맞지 않는 번호만 재설정됩니다.", "회원번호")) return;
      const errors = [];
      for (const r of rows.filter(offRule)) {
        const result = await renumber(r, { renumber: true });
        if (result.error) errors.push(`${r.userId} : ${result.error.split("\n")[0]}`);
        list.select(r);
      }
      await ctx.msgBox(errors.length ? `변환완료\n${errors.join("\n")}` : "변환완료");
      search();
    });
    $("combo_level").addEventListener("change", search);
    $("checkBox1").addEventListener("change", search);
    search();
  },
};
