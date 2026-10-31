// 반납 (BookReturn.cs). Enter a book barcode to return it; the borrower is looked up
// from the loan, so no member number is needed.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.BookReturn = {
  server: true,
  // Same split as 대출. List_SizeChanged() divides the member list by 4 for 5 columns,
  // so it overflows into a horizontal scrollbar just like CLIB.
  layout: { right: "controlpanel", ratios: { userpanel: 40, bookpanel: 59 }, columns: { userlist: 4, booklist: 6 } },

  init(ctx) {
    // 도서목록 shows only the member's current loans, so a book drops off it once returned
    const c = window.CLIB_circulation(ctx, {
      countText: u => `${u.lentCount}/${u.maxLend}`,
      bookRows: u => u.loans.map(l => ({ bookState: l.state, barcode: l.barcode, title: l.book.title,
        author: l.book.author, lendDate: l.lentDate, returnDate: l.dueDate })),
    });
    const { $, lib } = c;

    async function returnBook() {
      const barcode = $("txt_bookcode").value.trim();
      if (!barcode) {
        await ctx.msgBox("도서 등록번호를 입력해주세요");
        return c.focusSelect("txt_bookcode");
      }
      const book = await c.showBook(barcode);
      if (!book) return;
      if (book.loan) await c.selectUser(book.loan.userId, { quiet: true });
      const answers = {};
      let result = await lib.returnBook(barcode);
      while (result.confirm) {
        answers[result.ask || "attach"] = await ctx.confirm(result.confirm, result.title);
        result = await lib.returnBook(barcode, answers);
      }
      if (result.cancelled) return c.focusSelect("txt_bookcode");
      if (result.error) {
        await ctx.msgBox(result.error);
        return c.focusSelect("txt_bookcode");
      }
      await c.showAll(result.messages);
      const user = await c.selectUser(result.userId, { quiet: true });
      await c.showBook(result.barcode || barcode);
      await ctx.notice("LentMsg", { mode: 1, userName: user && user.userName, userId: result.userId,
        barcode: result.barcode || book.barcode });
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
        await c.selectUser(result.loan.userId, { quiet: true });
        await c.showBook(barcode);
      }
    }

    c.onEnter("txt_bookcode", returnBook);
    $("btn_return").addEventListener("click", returnBook);
    $("btn_extend").addEventListener("click", extend);
    ctx.dialogButton("btn_searchReturn", "ReturnSearch");
    ctx.notPorted("btn_attach");
  },
};
