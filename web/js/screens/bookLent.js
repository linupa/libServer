// 대출 (BookLent.cs). Enter a member number, then a book barcode, to lend.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.BookLent = {
  server: true,
  // BookLent_SizeChanged(): member list 40% / book list 59% on the left, controls fixed on the right.
  // List_SizeChanged() splits (width - 50) by 5 and 6.
  layout: { right: "controlpanel", ratios: { userpanel: 40, bookpanel: 59 }, columns: { userlist: 5, booklist: 6 } },

  init(ctx) {
    const c = window.CLIB_circulation(ctx, {
      countText: u => `${u.lentCount}/${u.maxLend}`,
      bookRows: u => u.loans.map(l => ({ bookState: l.state, barcode: l.barcode, title: l.book.title,
        author: l.book.author, lendDate: l.lentDate, returnDate: l.dueDate })),
    });
    const { $, lib } = c;

    async function lend() {
      const userId = $("txt_usercode").value.trim();
      const barcode = $("txt_bookcode").value.trim();
      if (!userId) {
        await ctx.msgBox("회원번호를 입력해주세요");
        return c.focusSelect("txt_usercode");
      }
      if (!barcode) {
        await ctx.msgBox("도서 등록번호를 입력해주세요");
        return c.focusSelect("txt_bookcode");
      }
      if (!await c.selectUser(userId) || !await c.showBook(barcode)) return;
      // 재대출 관리 asks whether to lend again (아니요 stops); 딸림자료 asks whether to
      // lend it along (아니요 lends the book alone)
      const answers = {};
      let result = await lib.lend(userId, barcode);
      while (result.confirm) {
        answers[result.ask] = await ctx.confirm(result.confirm, result.title);
        result = await lib.lend(userId, barcode, answers);
      }
      if (result.cancelled) return c.focusSelect("txt_bookcode");
      if (result.error) {
        await ctx.msgBox(result.error);
        return c.focusSelect("txt_bookcode");
      }
      const user = await c.selectUser(userId);
      const book = await c.showBook(result.loan.barcode);
      await ctx.notice("LentMsg", { mode: 0, userName: user && user.userName, userId: result.loan.userId,
        barcode: result.loan.barcode, lentDate: result.loan.lentDate, dueDate: result.loan.dueDate || (book && book.loan && book.loan.dueDate) });
      c.focusSelect("txt_bookcode");
    }

    async function extend() {
      const barcode = $("txt_bookcode").value.trim();
      if (!barcode) {
        await ctx.msgBox("도서 등록번호를 입력해주세요");
        return c.focusSelect("txt_bookcode");
      }
      const result = await lib.extend(barcode);
      await ctx.msgBox(result.error || result.message);
      if (result.ok) {
        await c.selectUser(result.loan.userId);
        await c.showBook(barcode);
      }
    }

    c.onEnter("txt_bookcode", lend);
    $("btn_lent").addEventListener("click", lend);
    $("btn_ExtendLent").addEventListener("click", extend);
    ctx.notPorted("btn_exLent");
  },
};
