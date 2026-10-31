// 예약 (BookReserve.cs). Enter a member number, then the barcode of a book that is
// out on loan, to join its waiting list. 도서목록 shows the member's reservations.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.BookReserve = {
  server: true,
  // List_SizeChanged() divides by 4 (5 member columns) and 7 (7 book columns)
  layout: { right: "controlpanel", ratios: { userpanel: 40, bookpanel: 59 }, columns: { userlist: 4, booklist: 7 } },

  init(ctx) {
    const c = window.CLIB_circulation(ctx, {
      countText: u => `${u.reserveCount}/${u.maxReserve}`,
      bookRows: u => u.reservations.map(r => ({
        bookState: r.book.state, borrower: r.book.loan ? r.book.loan.userName : "", barcode: r.book.barcode,
        title: r.book.title, author: r.book.author,
        lendDate: r.book.loan ? r.book.loan.lentDate : "", returnDate: r.book.loan ? r.book.loan.dueDate : "",
      })),
    });
    const { $, lib } = c;

    async function inputs() {
      const userId = $("txt_usercode").value.trim();
      const barcode = $("txt_bookcode").value.trim();
      if (!userId) {
        await ctx.msgBox("회원번호를 입력해주세요");
        c.focusSelect("txt_usercode");
        return null;
      }
      if (!barcode) {
        await ctx.msgBox("도서 등록번호를 입력해주세요");
        c.focusSelect("txt_bookcode");
        return null;
      }
      if (!await c.selectUser(userId) || !await c.showBook(barcode)) return null;
      return { userId, barcode };
    }

    async function reserve() {
      const v = await inputs();
      if (!v) return;
      const result = await lib.reserve(v.userId, v.barcode);
      if (result.error) await ctx.msgBox(result.error);
      const user = await c.selectUser(v.userId);
      await c.showBook(v.barcode);
      if (result.ok) {
        await ctx.notice("LentMsg", { mode: 2, userName: user && user.userName, userId: v.userId,
          barcode: result.barcode || v.barcode });
      }
      c.focusSelect("txt_bookcode");
    }

    async function cancel() {
      const v = await inputs();
      if (!v) return;
      const result = await lib.cancelReserve(v.userId, v.barcode);
      await ctx.msgBox(result.error || result.message);
      await c.selectUser(v.userId);
      await c.showBook(v.barcode);
    }

    c.onEnter("txt_bookcode", reserve);
    $("btn_reserve").addEventListener("click", reserve);
    $("btn_cancle").addEventListener("click", cancel);
  },
};
