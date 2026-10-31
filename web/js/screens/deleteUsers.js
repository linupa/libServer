// 삭제한 회원번호관리 (DeleteUsers.cs): members deleted in 회원관리 (DELETE_YN 'Y') with the
// loans, returns and overdue notes recorded up to the deletion. 삭제 clears the number and that
// history for good; 삭제취소 brings the member back.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.DeleteUsers = {
  server: true,

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("deleteGrid");
    let rows = [];

    // InitList()
    async function load() {
      rows = (await lib.deletedUsers()).map((u, i) => ({
        no: i + 1, check: false, userId: u.userId, userName: u.userName, deleteDate: u.deleteDate,
        lent: u.lent, returned: u.returned, overdue: u.overdue, delete: "기록삭제", undelete: "삭제취소" }));
      list.setRows(rows);
      if (!rows.length) await ctx.msgBox("조회된 삭제 회원이 없습니다.");
    }

    // DeleteUserCode() / ReUseUserCode(); a refusal only shows for a single member
    async function purge(r) {
      return lib.purgeUser(r.userId, r.deleteDate);
    }
    async function restore(r, quiet) {
      const result = await lib.restoreUser(r.userId);
      if (result.error && !quiet) await ctx.msgBox(result.error);
      return result;
    }

    list.onButton(async (r, key) => {
      if (key === "delete") {
        if (!await ctx.confirm("해당 회원번호 기록을 삭제하시겠습니까?\n※삭제한 회원번호 정보는 복구할 수 없습니다.", "회원번호 삭제")) return;
        if ((r.lent > 0 || r.returned > 0 || r.overdue > 0) &&
            !await ctx.confirm("사용이력이 있는 회원번호입니다.\n삭제하시겠습니까?\n※해당 회원번호로 기록된 이용내역은 모두 삭제됩니다.", "회원번호 삭제")) return;
        const result = await purge(r);
        if (result.error) return ctx.msgBox(result.error);
      } else {
        if (!await ctx.confirm("해당 회원번호의 삭제를 취소하시겠습니까?", "회원복구")) return;
        if ((await restore(r)).error) return;
      }
      load();
    });

    // 전체선택 checks every row, then clears them (the button says which comes next)
    let all = false;
    $("btn_AllSel").addEventListener("click", () => {
      all = !all;
      rows.forEach(r => { r.check = all; });
      $("btn_AllSel").textContent = all ? "전체해제" : "전체체크";
      list.refresh();
    });

    function checked() {
      const picked = rows.filter(r => r.check);
      if (!picked.length) ctx.msgBox("선택된 회원이 없습니다.");
      return picked;
    }
    $("btn_batchDelete").addEventListener("click", async () => {
      const picked = checked();
      if (!picked.length) return;
      // CLIB deletes without asking; the history can't be brought back, so ask once here
      if (!await ctx.confirm("선택한 회원번호 기록을 모두 삭제하시겠습니까?\n※해당 회원번호로 기록된 이용내역은 모두 삭제되며 복구할 수 없습니다.", "회원번호 삭제")) return;
      for (const r of picked) await purge(r);
      await load();
      await ctx.msgBox("완료되었습니다.");
    });
    $("btn_BatchReUse").addEventListener("click", async () => {
      const picked = checked();
      if (!picked.length) return;
      for (const r of picked) await restore(r, true);
      await load();
      await ctx.msgBox("완료되었습니다.");
    });

    load();
  },
};
