// 연체관리 (BookDelay.cs): 연체회원 (members who are 연체중), 연체도서 (loans past their due
// date), or 연체회원 with 연체도서 같이 보기 (each member's overdue books). The three grids sit in
// the same place and one is shown at a time. With 연체금 납부 (LENT_OPTION.DELAY 2) the fee
// columns show what each member owes.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.BookDelay = {
  server: true,
  // The constructor moves every grid to (11, 89) and sizes it to the form (Height - 131)
  arrange({ root, nodes, render }) {
    for (const n of nodes) {
      const el = render(n);
      if (n.type === "list") el.style.cssText = `left:${n.x}px;top:89px;right:12px;bottom:3px`;
      root.append(el);
    }
  },
  // 순번 follows the shown order (booklist_Sorted / delaylist_Sorted)
  lists: { userlist: { renumber: true }, booklist: { renumber: true }, delaylist: { renumber: true } },

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const LISTS = ["userlist", "booklist", "delaylist"];
    const lists = Object.fromEntries(LISTS.map(id => [id, ctx.list(id)]));
    let shown = "delaylist";

    // DELAY 2 = 연체금 납부: show 연체금, 미납금 and 총 연체금
    const L = lib.settings.lend;
    const fees = L.delay === 2;
    if (!fees) {
      lists.userlist.hideColumns(["overdueFee", "unpaidFee", "totalFee"]);
      lists.delaylist.hideColumns(["unpaidFee", "overdueFee", "totalFee"]);
    }

    const fill = (name, values) => $(name).replaceChildren(...values.map(v =>
      Object.assign(document.createElement("option"), { value: v, textContent: v })));
    // Swap_Combo(): what the keyword is matched against, and 연체도서 같이 보기 for members only
    function swapCombo() {
      const members = $("combo_index1").value === "연체회원";
      fill("combo_index2", members ? ["회원번호", "회원명"] : ["도서번호", "도서명"]);
      ctx.box("chk_book").hidden = !members;
    }
    // Swap_List(): the grid for the search, then search again with an empty keyword
    function swapList() {
      shown = $("combo_index1").value === "연체도서" ? "booklist" : $("chk_book").checked ? "delaylist" : "userlist";
      for (const id of LISTS) ctx.box(id).hidden = id !== shown;
    }

    const day = s => { const [y, m, d] = s.split("-").map(Number); return Date.UTC(y, m - 1, d); };
    const lateDays = due => (due ? Math.round((day(lib.today()) - day(due)) / 86400000) : 0);

    async function search() {
      const { users, loans } = await lib.overdue();
      const kw = $("txt_keyword").value.trim().toLowerCase();
      const by = $("combo_index2").value;
      // 연체금: every overdue day of the member's books x DELAY_CHARGE; with the unpaid amount,
      // up to DELAY_MAX
      const owed = id => {
        const fee = loans.filter(l => l.userId === id).reduce((n, l) => n + lateDays(l.dueDate), 0) * L.delayCharge;
        const unpaid = Number((users.find(u => u.userId === id) || loans.find(l => l.userId === id) || {}).unpaid) || 0;
        return fees ? { overdueFee: fee, unpaidFee: unpaid, totalFee: Math.min(fee + unpaid, L.delayChargeMax) } : {};
      };
      // 회원번호 is matched whole, 회원명 anywhere (SearchUser())
      const memberMatch = r => !kw || (by === "회원번호" ? r.userId.toLowerCase() === kw : r.userName.toLowerCase().includes(kw));

      if (shown === "userlist") {
        lists.userlist.setRows(users.filter(memberMatch).map(u => ({
          userId: u.userId, userName: u.userName, userGrade: u.userGrade, userState: u.userState,
          overdueCount: u.overdueCount, phone: u.phone, email: u.email, ...owed(u.userId) })));
      } else if (shown === "booklist") {
        // 도서번호 is matched whole, 도서명 anywhere with spaces ignored (SearchBook())
        const flat = s => String(s || "").replace(/\s/g, "").toLowerCase();
        lists.booklist.setRows(loans
          .filter(l => !kw || (by === "도서번호" ? l.barcode.toLowerCase() === kw : flat(l.title).includes(flat(kw))))
          .map(l => ({ bookState: l.bookState, barcode: l.barcode, title: `${l.title}.${l.volume || ""}`, author: l.author,
            borrower: l.userName, claim: l.claim, lendDate: l.lentDate, returnDate: l.dueDate,
            overdueDays: l.dueDate ? String(lateDays(l.dueDate)) : "" })));
      } else {
        // SearchUser_Book(): by member, then due date. CLIB ignores the keyword here; it is applied
        // as for 연체회원.
        lists.delaylist.setRows(loans.filter(l => l.dueDate && memberMatch(l))
          .sort((a, b) => a.userId.localeCompare(b.userId) || a.dueDate.localeCompare(b.dueDate))
          .map(l => ({ userId: l.userId, userName: l.userName, phone: l.phone, address: l.address, email: l.email,
            title: l.title, lendDate: l.lentDate, returnDate: l.dueDate, overdueDays: `${lateDays(l.dueDate)}일`,
            ...owed(l.userId) })));
      }
    }

    $("combo_index1").addEventListener("change", () => {
      swapCombo();
      swapList();
      $("txt_keyword").value = "";
      search();
    });
    $("chk_book").addEventListener("change", () => { swapList(); search(); });
    $("btn_search").addEventListener("click", search);
    $("txt_keyword").addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) search(); });
    // 파일로 저장: the grid on screen
    $("btn_save").addEventListener("click", () => lists[shown].exportCsv());

    $("combo_index1").value = "연체회원";
    swapCombo();
    swapList();
    search();
  },
};
