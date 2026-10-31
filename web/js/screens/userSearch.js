// 회원검색 (UserSearch.cs): find members and hand the checked ones, or all of them (전체
// 불러오기, in place of CLIB's 전체선택), back to the screen that opened the dialog (회원관리,
// 대출, 반납, 예약).
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.UserSearch = {
  server: true,
  ownClose: true, // CLIB's dialog has no 닫기 button, only the window's X

  arrange({ root, nodes, render, controls }) {
    // 전체 불러오기 sits left of 불러오기 (461, 55)
    const all = Object.assign(document.createElement("button"), { type: "button", className: "ctl btn", id: "UserSearch-btn_loadAll", textContent: "전체 불러오기" });
    all.style.cssText = "left:360px;top:55px;width:95px;height:25px";
    controls.btn_loadAll = all;
    root.append(all);
    for (const n of nodes) {
      const el = render(n);
      if (n.id === "userlist") el.style.cssText = `left:${n.x}px;top:${n.y}px;right:2px;bottom:2px`;
      root.append(el);
    }
  },

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("userlist");
    let rows = [];

    // 회원등급 and 회원상태 pick from a list instead of typing
    function syncIndex() {
      const field = $("combo_index").value;
      const choices = field === "회원등급" ? lib.grades.map(g => g.grade) : field === "회원상태" ? lib.codes.userState : null;
      ctx.box("txt_keyword").hidden = !!choices;
      ctx.box("combo_index2").hidden = !choices;
      if (choices) $("combo_index2").replaceChildren(...choices.map(v => Object.assign(document.createElement("option"), { value: v, textContent: v })));
    }
    $("combo_index").addEventListener("change", syncIndex);
    syncIndex();

    async function search() {
      const field = $("combo_index").value;
      const keyword = ctx.box("combo_index2").hidden ? $("txt_keyword").value : $("combo_index2").value;
      rows = (await lib.searchUsers(field, keyword)).map((u, i) => ({
        checked: false, no: i + 1, userId: u.userId, userName: u.userName, userGrade: u.userGrade,
        userState: u.userState, phone: u.phone, address: u.address, email: u.email, lendDays: u.lendDays,
        maxLend: u.maxLend, maxReserve: u.maxReserve,
        suspendUntil: u.suspendUntil,
        regDate: u.regDate,
      }));
      list.setRows(rows);
      if (!rows.length) ctx.msgBox("검색 결과가 없습니다.");
    }

    // all: every searched member, checked or not
    function load(all) {
      if (all && !rows.length) return ctx.msgBox("검색된 회원이 없습니다.");
      const picked = all ? rows : rows.filter(r => r.checked);
      const chosen = picked.length ? picked : list.selected() ? [list.selected()] : [];
      if (!chosen.length) return ctx.msgBox("선택된 회원이 없습니다.");
      // The search rows already carry what the member lists show, so they are handed over
      // as they are instead of being fetched again one by one
      ctx.bus.emit("loadUsers", chosen.map(({ checked, no, ...u }) => u));
      ctx.close();
    }

    $("btn_search").addEventListener("click", search);
    $("txt_keyword").addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) search(); });
    $("btn_userload").addEventListener("click", () => load(false));
    $("btn_loadAll").addEventListener("click", () => load(true));
    list.onRowClick(() => {});
    setTimeout(() => $("txt_keyword").focus());
  },
};
