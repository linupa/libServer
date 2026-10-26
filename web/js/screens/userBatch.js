// 일괄수정 > 회원상태 수정 / 회원등급 수정 (UserBatchDlg.cs): pick the new state or grade; 회원관리
// then saves it for every member checked in its list (BatchProcess.cs).
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
(function () {
  // field: "userState" (UserBatchDlg(1)) or "userGrade" (UserBatchDlg(0))
  const batchDialog = field => ({
    server: true,
    ownClose: true, // ControlBox = false; 수정 and 취소 close it

    init(ctx) {
      const lib = ctx.library;
      const $ = ctx.input;
      // LoadingCombo(): CODE_SUB 000 (회원등급) or 003 (회원상태), in code order
      ctx.box("label1").textContent = field === "userGrade" ? "회원등급" : "회원상태";
      const values = field === "userGrade" ? lib.grades.map(g => g.grade) : lib.codes.userState;
      $("combo_Batch").replaceChildren(...values.map(v =>
        Object.assign(document.createElement("option"), { value: v, textContent: v })));
      $("btn_cancle").addEventListener("click", () => ctx.close());
      $("btn_run").addEventListener("click", () => {
        const value = $("combo_Batch").value;
        ctx.close();
        ctx.bus.emit("batchEditUsers", { field, value });
      });
    },
  });
  window.CLIB_LOGIC.UserBatchState = batchDialog("userState");
  window.CLIB_LOGIC.UserBatchLevel = batchDialog("userGrade");
})();
