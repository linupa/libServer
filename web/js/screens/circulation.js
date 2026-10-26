// Shared parts of 대출 / 반납 / 예약 (BookLent.cs, BookReturn.cs, BookReserve.cs):
// the 회원정보 box, the session 회원목록, and the book details box.
window.CLIB_circulation = function (ctx, { bookRows, countText }) {
  const lib = ctx.library;
  const $ = ctx.input;
  const userList = ctx.list("userlist");
  const bookList = ctx.list("booklist");
  const sessionUsers = [];
  const BOOK_FIELDS = ["txt_bookcode", "txt_lentDate", "txt_returnDate", "txt_bookName", "txt_author",
    "txt_location", "txt_bookState", "txt_publish", "txt_category", "txt_attach", "txt_claim"];

  const set = (name, value) => { $(name).value = value ?? ""; };
  const focusSelect = name => { $(name).focus(); $(name).select(); };
  const clearBook = (keepCode = false) => BOOK_FIELDS.slice(keepCode ? 1 : 0).forEach(n => set(n, ""));
  if (!lib.isServer) {
    $("txt_usercode").title = "샘플 회원번호: AA0001-AA0010 (Child), AB0001-AB0015 (Adult), AD0001-AD0002, PR0001-PR0003";
    $("txt_bookcode").title = "샘플 등록번호: EM000001-EM000120";
  }

  // SelectUser(): fill 회원정보, list the member's books, remember the member in 회원목록.
  // Library calls are awaited so the same code works with the sample data and the server.
  async function selectUser(id, { quiet = false } = {}) {
    const user = await lib.findUser(id);
    if (!user) {
      if (!quiet) ctx.msgBox("해당하는 회원이 없습니다.").then(() => focusSelect("txt_usercode"));
      return null;
    }
    set("txt_usercode", user.userId);
    set("txt_username", user.userName);
    set("txt_phone", user.phone);
    set("txt_lentmax", countText(user));
    set("txt_userlevel", user.userGrade);
    set("txt_userstate", user.userState);
    set("txt_address", user.address);
    set("txt_memo", [user.memo, user.unpaid ? `미납 연체금 : ${user.unpaid} 원` : ""].filter(Boolean).join("\n"));
    bookList.setRows(bookRows(user).map((r, i) => ({ no: i + 1, ...r })));
    if (!sessionUsers.some(u => u.userId === user.userId)) {
      sessionUsers.push({ no: sessionUsers.length + 1, userId: user.userId, userName: user.userName,
        userState: user.userState, userGrade: user.userGrade, phone: user.phone });
      userList.setRows([...sessionUsers]);
    }
    return user;
  }

  // SelectBook(): fill the book details box
  async function showBook(barcode, { quiet = false } = {}) {
    const book = await lib.findBook(barcode);
    if (!book) {
      if (!quiet) ctx.msgBox("해당하는 도서가 없습니다.").then(() => focusSelect("txt_bookcode"));
      return null;
    }
    set("txt_bookcode", book.barcode);
    set("txt_bookName", book.title);
    set("txt_author", book.author);
    set("txt_location", book.location);
    set("txt_bookState", book.state);
    set("txt_publish", book.publisher);
    set("txt_category", book.category);
    set("txt_attach", book.attach);
    set("txt_claim", book.claim);
    set("txt_lentDate", book.loan ? book.loan.lentDate : "");
    set("txt_returnDate", book.loan ? book.loan.dueDate : "");
    return book;
  }

  const onEnter = (name, fn) => $(name).addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); fn(); }
  });

  onEnter("txt_usercode", async () => {
    clearBook();
    if (await selectUser($("txt_usercode").value)) focusSelect("txt_bookcode");
  });
  onEnter("txt_username", async () => {
    const name = $("txt_username").value.trim();
    if (!name) return;
    const found = await lib.findUsersByName(name);
    if (found.length === 1) {
      if (await selectUser(found[0].userId)) focusSelect("txt_bookcode");
    } else if (found.length) {
      ctx.openDialog("UserSearch");
    } else {
      ctx.msgBox("해당하는 회원이 없습니다.");
    }
  });
  onEnter("txt_bookName", () => ctx.openDialog("SearchBooks"));
  ctx.dialogButton("btn_userSearch", "UserSearch");
  ctx.dialogButton("btn_bookSearch", "SearchBooks");
  userList.onRowClick(row => { clearBook(); selectUser(row.userId); });
  bookList.onRowClick(row => showBook(row.barcode));
  setTimeout(() => $("txt_usercode").focus());

  // 회원검색 hands members back: add them to 회원목록 and select the first (InsertUserList)
  // 회원검색 hands back the members' list rows; only the first one is fetched in full
  const offLoad = ctx.bus.on("loadUsers", async users => {
    if (!$("txt_usercode").isConnected) return offLoad();
    for (const u of users) {
      if (sessionUsers.some(s => s.userId === u.userId)) continue;
      sessionUsers.push({ no: sessionUsers.length + 1, userId: u.userId, userName: u.userName,
        userState: u.userState, userGrade: u.userGrade, phone: u.phone });
    }
    userList.setRows([...sessionUsers]);
    if (users.length) await selectUser(users[0].userId, { quiet: true });
  });

  // Shows each message in turn, like CLIB's consecutive MessageBox.Show() calls
  async function showAll(messages) {
    for (const m of messages) await ctx.msgBox(m);
  }

  return { lib, $, set, focusSelect, clearBook, selectUser, showBook, onEnter, showAll };
};
