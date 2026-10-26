// 회원일괄입력 (BatchInput.cs): members from an Excel or CSV file laid out like CLIB's
// Sample\Users.xls (회원번호, 성명, 전화번호, 주소, 이메일, 회원등급 under a heading row). Each
// row is saved as 회원관리 saves a new member; the rows that fail stay in the list with the
// reason. Numbers already in use, or left by deleted members, can then be entered anyway with
// 중복된 번호 입력 / 삭제된 번호 입력.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.BatchInput = {
  server: true,

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("userlist");
    let rows = [];
    const OVERLAP = "사용중인 회원번호", DELETED = "삭제된 회원번호";

    // SaveUsers()'s answers in batch mode, as the list shows them
    function reason(result) {
      if (result.ask === "deletedCode") return DELETED;
      if (result.ask === "overwrite") return OVERLAP;
      const e = String(result.error || "");
      if (e.includes("회원명")) return "회원명 오류";
      if (e.includes("회원번호")) return "회원번호 오류";
      if (e.includes("등급")) return "회원등급 오류";
      return e.split("\n")[0] || "저장 실패";
    }
    function redraw() {
      list.setRows(rows);
      ctx.box("btn_Overlap").hidden = !rows.some(r => r.failReason === OVERLAP);
      ctx.box("btn_Delete").hidden = !rows.some(r => r.failReason === DELETED);
    }
    const record = r => ({ userId: r.userId.trim().toUpperCase(), userName: r.userName.trim(), phone: r.phone.trim(),
      address: r.address.trim(), email: r.email.trim(), userGrade: r.userGrade.trim(), userState: "정상", memo: "", isNew: true });

    // 파일불러오기: the first sheet, from the second row until the first row without 회원번호
    const picker = Object.assign(document.createElement("input"), { type: "file", accept: ".xls,.xlsx,.csv", hidden: true });
    ctx.box("btn_open").after(picker);
    $("btn_open").addEventListener("click", () => picker.click());
    picker.addEventListener("change", async () => {
      const file = picker.files[0];
      picker.value = "";
      if (!file) return;
      let sheet;
      try {
        sheet = await window.CLIB.readSheet(file);
      } catch (e) {
        return ctx.msgBox(`파일을 읽을 수 없습니다.\n${e.message}`);
      }
      const data = [];
      for (const cells of sheet.slice(1)) {
        if (!String(cells[0] ?? "").trim()) break;
        const [userId, userName, phone, address, email, userGrade] = Array.from({ length: 6 }, (_, i) => String(cells[i] ?? ""));
        data.push({ userId, userName, phone, address, email, userGrade });
      }
      rows = [];
      redraw();
      $("btn_open").disabled = true;
      let saved = 0;
      try {
        for (const [i, r] of data.entries()) {
          $("btn_open").textContent = `입력중 ${i + 1}/${data.length}`;
          const result = await lib.saveUser(record(r), {});
          if (result.ok) saved++;
          else rows.push({ ...r, failReason: reason(result) });
        }
      } finally {
        $("btn_open").textContent = "파일불러오기";
        $("btn_open").disabled = false;
        redraw();
      }
      await ctx.msgBox(`완료되었습니다.\n입력 : ${saved} 명 / 실패 : ${rows.length} 명`);
    });

    // btn_Overlap_Click / btn_Delete_Click: enter the rows with that reason again, answering yes
    async function enterAgain(why, question, answers) {
      if (!await ctx.confirm(question, "일괄입력")) return;
      for (const r of rows.filter(x => x.failReason === why)) {
        const result = await lib.saveUser(record(r), { ...answers });
        if (result.ok) rows.splice(rows.indexOf(r), 1);
        else r.failReason = reason(result);
      }
      redraw();
      await ctx.msgBox("완료되었습니다.");
    }
    $("btn_Overlap").addEventListener("click", () => enterAgain(OVERLAP, "중복된 회원번호를 일괄입력 하시겠습니까?", { overwrite: true }));
    $("btn_Delete").addEventListener("click", () => enterAgain(DELETED,
      "삭제된 회원번호를 일괄입력 하시겠습니까?\n※ 삭제된 회원번호를 재사용할 경우,\n해당 번호로 사용된 대출/반납 기록은 삭제됩니다.", { deletedCode: true }));
    // 샘플파일보기: CLIB's Sample\Users.xls
    $("btn_sample").addEventListener("click", () => {
      const a = Object.assign(document.createElement("a"), { href: "sample/Users.xls", download: "Users.xls" });
      document.body.append(a);
      a.click();
      a.remove();
    });
  },
};
