// 회원관리 (Users.cs): the member list on the left, the member editor and card preview on the right.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.Users = {
  server: true,
  // Users_SizeChanged(): userpanel = form width - 530 by form height - 15; the list fills it
  // (width - 25, height - 40). The buttons over the list follow 도서관리's: 전체선택 and
  // 파일로 저장 at its left edge (like 전체선택 / Excel 샘플), 화면지우기 and 일괄삭제 at its
  // right edge (like 새작업 … 일괄삭제), the same sizes, gaps and bold text; no 회원목록 caption.
  arrange({ root, nodes, render, controls }) {
    const TOP_BUTTONS = {
      btn_AllSel: { left: 1, w: 73 }, btn_filesave: { left: 88, w: 88 },
      btn_initValue: { right: 81, w: 73 }, btn_batchDelete: { right: 2, w: 73 },
    };
    root.classList.add("split");
    const left = Object.assign(document.createElement("div"), { className: "form-left" });
    const right = Object.assign(document.createElement("div"), { className: "form-right" });
    root.append(left, right);
    for (const n of nodes) {
      const el = render(n);
      if (n.id === "controlpanel") {
        right.style.width = `${n.w}px`;
        el.style.cssText = `left:0;top:0;width:${n.w}px;height:${n.h}px`;
        right.append(el);
        continue;
      }
      el.classList.add("stretch");
      el.style.cssText = "flex:1 1 0";
      left.append(el);
      const list = n.children.find(c => c.id === "userlist");
      const LIST_RIGHT = 25 - list.x; // the list's right edge, from the panel's
      const LIST_TOP = 33; // 7px under the buttons, as in 도서관리
      for (const c of n.children) {
        const box = controls[`${c.id}:box`];
        if (c.id === "userlist") box.style.cssText = `left:${c.x}px;top:${LIST_TOP}px;right:${LIST_RIGHT}px;bottom:${40 - c.y}px`;
        if (c.id === "label1") box.hidden = true;
        const b = TOP_BUTTONS[c.id];
        if (b) {
          box.style.width = `${b.w}px`;
          box.style.fontWeight = "bold";
          if (b.right !== undefined) Object.assign(box.style, { left: "auto", right: `${LIST_RIGHT + b.right}px` });
          else box.style.left = `${list.x + b.left}px`;
        }
      }
    }
  },

  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const list = ctx.list("userlist");
    let rows = [];
    let current = null; // userId being edited, null for a new member
    let pickedPhoto = null; // a photo chosen with 파일찾기, saved with the member

    // Users_Load(): 연체금 and 연체금 완납 show only with 연체금 납부 (LENT_OPTION.DELAY 2), and
    // the memo box is narrower then; 사진불러오기's label is hidden
    const charges = lib.settings.lend.delay >= 2;
    ["label17", "label18", "txt_charge", "btn_charge"].forEach(n => { ctx.box(n).hidden = !charges; });
    ctx.box("label10").hidden = true;
    ctx.box("txt_memo").style.width = `${charges ? 237 : 395}px`;
    $("txt_charge").readOnly = true;
    $("txt_charge").style.textAlign = "right";

    const fill = (name, values) => $(name).replaceChildren(...values.map(v =>
      Object.assign(document.createElement("option"), { value: v, textContent: v })));
    fill("combo_Userlevel", lib.grades.map(g => g.grade));
    fill("combo_UserState", lib.codes.userState);

    // 회원증 미리보기 (panel1)
    ctx.box("label_library").textContent = lib.settings.library.name;
    ctx.box("label_library").style.cssText += ";justify-content:center;font-weight:700";
    // picture_barcode holds the Code 39 image, label_barcode the number under it
    const img = ctx.box("pictureBox1").querySelector("img");
    img.onload = () => { img.hidden = false; };
    img.onerror = () => { img.hidden = true; };
    let photoVersion = 0; // bumped after a photo is saved, so the new one is fetched
    function preview(user) {
      // The member's saved photo (USER_IMAGE), when the file can be found
      img.hidden = true;
      img.removeAttribute("src");
      const url = user && lib.photoUrl && lib.photoUrl(user.userId, photoVersion);
      if (url) img.src = url;
      ctx.box("label_name").textContent = user ? user.userName : "";
      ctx.box("label_date").textContent = user ? user.regDate : "";
      ctx.box("label_barcode").textContent = user ? user.userId : "";
      ctx.box("picture_barcode").innerHTML = user ? window.CLIB.code39(user.userId, 27) : "";
    }

    function toRow(u) {
      return { checked: false, userId: u.userId, userName: u.userName, userGrade: u.userGrade,
        userState: u.userState, phone: u.phone, address: u.address, email: u.email,
        lendDays: u.lendDays, maxLend: u.maxLend, maxReserve: u.maxReserve, regDate: u.regDate };
    }
    function redraw(select) {
      rows.forEach((r, i) => { r.no = i + 1; });
      list.setRows(rows);
      if (select) list.select(select);
    }
    function addUsers(users) {
      for (const u of users) {
        const i = rows.findIndex(r => r.userId === u.userId);
        if (i >= 0) rows[i] = Object.assign(toRow(u), { checked: rows[i].checked });
        else rows.push(toRow(u));
      }
      redraw();
    }

    function show(user) {
      current = user ? user.userId : null;
      $("combo_Userlevel").value = user ? user.userGrade : lib.grades[0].grade;
      $("txt_usercode").value = user ? user.userId : "";
      $("txt_username").value = user ? user.userName : "";
      $("txt_phone").value = user ? user.phone : "";
      $("txt_address").value = user ? user.address : "";
      $("txt_email").value = user ? user.email : "";
      $("combo_UserState").value = user ? user.userState : "정상";
      const g = lib.grades.find(x => x.grade === $("combo_Userlevel").value);
      $("txt_lentmax").value = user ? `${user.lentCount}/${user.maxLend}` : `0/${g.maxLend}`;
      $("txt_maxreserve").value = user ? `${user.reserveCount}/${user.maxReserve}` : `0/${g.maxReserve}`;
      $("txt_diable_date").value = user ? user.suspendUntil : "";
      $("txt_memo").value = user ? user.memo : "";
      // 파일찾기's box shows where the photo is kept; a picked file belongs to this member only
      $("txt_folder").value = user ? user.photo || "" : "";
      pickedPhoto = null;
      $("txt_charge").value = user ? Number(user.unpaid) || 0 : "";
      preview(user);
    }

    // 신규: blank member with the next number for the chosen grade (USERCODE=1).
    // The grade on screen is kept, so several members of one grade can be added in a row.
    async function newUser() {
      const grade = $("combo_Userlevel").value;
      show(null);
      const g = lib.grades.find(x => x.grade === grade);
      if (g) {
        $("combo_Userlevel").value = grade;
        $("txt_lentmax").value = `0/${g.maxLend}`;
        $("txt_maxreserve").value = `0/${g.maxReserve}`;
      }
      $("txt_usercode").value = await lib.nextUserId($("combo_Userlevel").value);
      $("txt_username").focus();
    }
    $("combo_Userlevel").addEventListener("change", async () => {
      const g = lib.grades.find(x => x.grade === $("combo_Userlevel").value);
      if (!current) $("txt_usercode").value = await lib.nextUserId(g.grade);
      $("txt_lentmax").value = `${$("txt_lentmax").value.split("/")[0] || 0}/${g.maxLend}`;
      $("txt_maxreserve").value = `${$("txt_maxreserve").value.split("/")[0] || 0}/${g.maxReserve}`;
    });

    async function load() {
      const id = $("txt_usercode").value.trim();
      if (!id) return ctx.msgBox("조회할 회원번호를 입력해주세요.");
      const user = await lib.findUser(id);
      if (!user) return ctx.msgBox("해당하는 회원이 없습니다.");
      addUsers([user]);
      list.select(rows.find(r => r.userId === user.userId));
      show(user);
    }

    async function save() {
      const userId = $("txt_usercode").value.trim().toUpperCase();
      if (!userId) return ctx.msgBox("회원번호를 입력해주세요.");
      if (!/^[A-Z0-9]+$/.test(userId)) return ctx.msgBox("회원번호는 영어와 숫자만 가능합니다.");
      if (!$("txt_username").value.trim()) return ctx.msgBox("회원명을 입력해주세요.");
      const record = {
        userId, userName: $("txt_username").value.trim(), userGrade: $("combo_Userlevel").value,
        userState: $("combo_UserState").value, phone: $("txt_phone").value.trim(),
        address: $("txt_address").value.trim(), email: $("txt_email").value.trim(), memo: $("txt_memo").value,
        isNew: current !== userId,
      };
      const answers = {};
      let result = await lib.saveUser(record, answers);
      while (result.confirm) {
        answers[result.ask] = await ctx.confirm(result.confirm, result.title);
        result = await lib.saveUser(record, answers);
      }
      if (result.cancelled) return;
      if (result.error) return ctx.msgBox(result.error);
      // SaveUsers(): the chosen photo goes with the member (<회원번호>.<ext>)
      if (pickedPhoto) {
        const saved = await lib.savePhoto(userId, pickedPhoto);
        if (saved.error) await ctx.msgBox(saved.error);
        else photoVersion = Date.now();
      }
      const user = await lib.findUser(userId) || result.user;
      addUsers([user]);
      list.select(rows.find(r => r.userId === user.userId));
      show(user);
      await ctx.msgBox("저장되었습니다.");
    }

    const DELETE_CONFIRM = "선택한 회원을 삭제하시겠습니까?\n※ 현재 대출중, 연체중, 예약중인 회원은 삭제되지 않습니다.\n※ 삭제된 회원의 대출기록은 조회되지 않습니다.";

    async function remove() {
      if (!current) return ctx.msgBox("선택된 회원이 없습니다.");
      if (!await ctx.confirm(DELETE_CONFIRM, "회원삭제")) return;
      const result = await lib.deleteUser(current);
      if (result.error) return ctx.msgBox(result.error);
      rows = rows.filter(r => r.userId !== current);
      redraw();
      show(null);
      await ctx.msgBox("삭제되었습니다.");
    }

    async function batchDelete() {
      const picked = rows.filter(r => r.checked);
      if (!picked.length) return ctx.msgBox("선택된 회원이 없습니다.");
      if (!await ctx.confirm(DELETE_CONFIRM, "회원삭제")) return;
      // Members with loans or reservations are skipped, as the message says
      const before = rows.length;
      let refused = null;
      for (const r of picked) {
        const result = await lib.deleteUser(r.userId);
        if (result.ok) rows.splice(rows.indexOf(r), 1);
        else refused = refused || result.error;
      }
      // Nothing deleted (e.g. the read-only server): say why instead of "삭제되었습니다"
      if (rows.length === before && refused) return ctx.msgBox(refused);
      if (!rows.some(r => r.userId === current)) show(null);
      redraw();
      await ctx.msgBox("삭제되었습니다.");
    }

    // 파일찾기 (btn_folder_Click): shows the picture now; 저장 saves it with the member
    const file = Object.assign(document.createElement("input"), { type: "file", accept: ".jpg,.jpeg,.png,.gif,.bmp", hidden: true });
    ctx.box("groupBox2").append(file);
    file.addEventListener("change", () => {
      const f = file.files[0];
      file.value = "";
      if (!f) return;
      pickedPhoto = f;
      $("txt_folder").value = f.name;
      img.src = URL.createObjectURL(f);
    });

    // Other screens hand members back through the bus
    // 회원검색 hands back its list rows, which have every column; only the first is fetched in full
    const offLoad = ctx.bus.on("loadUsers", async users => {
      if (!ctx.box("userlist").isConnected) return offLoad();
      addUsers(users);
      const first = users[0] && await lib.findUser(users[0].userId);
      if (first) { list.select(rows.find(r => r.userId === first.userId)); show(first); }
    });
    // 회원증 출력 asks for the list's members and which are checked
    const offCollect = ctx.bus.on("collectUsers", out => {
      if (!ctx.box("userlist").isConnected) return offCollect();
      out.total = rows.length;
      // The list rows carry what the card needs (number, name, join date)
      out.users = rows.filter(r => r.checked);
    });

    // 일괄수정 (BatchProcess.UserStateFn / UserLevelFn): save the new state or grade for each
    // checked member; those saved are unchecked
    const offBatch = ctx.bus.on("batchEditUsers", async ({ field, value }) => {
      if (!ctx.box("userlist").isConnected) return offBatch();
      const picked = rows.filter(r => r.checked);
      if (!picked.length) return ctx.msgBox("선택된 회원이 없습니다.");
      const ask = `수정하시겠습니까?${field === "userGrade" ? "\n회원번호는 변동되지 않습니다." : ""}`;
      if (!await ctx.confirm(ask, "회원정보 수정")) return;
      const users = await lib.findUsers(picked.map(r => r.userId));
      const done = [];
      let failed = picked.length - users.length;
      for (const u of users) {
        const result = await lib.saveUser({
          userId: u.userId, userName: u.userName, userGrade: u.userGrade, userState: u.userState, phone: u.phone,
          address: u.address, email: u.email, memo: u.memo, isNew: false, [field]: value,
        }, {});
        if (result.ok) done.push(u.userId); else failed++;
      }
      const fresh = await lib.findUsers(done);
      addUsers(fresh);
      rows.filter(r => done.includes(r.userId)).forEach(r => { r.checked = false; });
      list.refresh();
      const shown = fresh.find(u => u.userId === current);
      if (shown) show(shown);
      await ctx.msgBox(`성공 : ${done.length} 명\n실패 : ${failed} 명`);
    });

    list.onRowClick(async r => show(await lib.findUser(r.userId)));
    const click = (n, fn) => $(n).addEventListener("click", fn);
    click("btn_New", newUser);
    click("btn_UserSave", save);
    click("btn_UserDelete", remove);
    ctx.dialogButton("btn_userSearch", "UserSearch");
    ctx.dialogButton("btn_batch", "BatchInput");
    // 이용내역 조회: the member whose 회원번호 is in the editor
    let statsFor = "";
    const offStats = ctx.bus.on("userLentStatsTarget", out => {
      if (!ctx.box("userlist").isConnected) return offStats();
      out.userId = statsFor;
    });
    click("btn_userstats", async () => {
      const id = $("txt_usercode").value.trim().toUpperCase();
      if (!id) return ctx.msgBox("조회할 회원번호를 입력해주세요.");
      if (!await lib.findUser(id)) return ctx.msgBox("해당하는 회원이 없습니다.");
      statsFor = id;
      ctx.openDialog("UserLentStats");
    });
    // 연체금 완납 (btn_charge_Click)
    click("btn_charge", async () => {
      if (!current) return ctx.msgBox("선택된 회원이 없습니다.");
      if (!await ctx.confirm("연체금을 완납처리 하시겠습니까?", "연체금관리")) return;
      const result = await lib.payCharge(current);
      if (result.error) return ctx.msgBox(result.error);
      const user = await lib.findUser(current);
      addUsers([user]);
      show(user);
    });
    click("btn_initValue", () => { rows = []; redraw(); show(null); });
    click("btn_batchDelete", batchDelete);
    click("btn_filesave", () => list.exportCsv());
    click("btn_AllSel", () => { const on = !rows.every(r => r.checked); rows.forEach(r => { r.checked = on; }); list.refresh(); });
    click("btn_folder", () => file.click());
    ctx.dialogButton("btn_joinPrint", "JoinPrint");
    $("txt_usercode").addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) load(); });
    if (!lib.isServer) $("txt_usercode").title = "샘플 회원번호: AA0001-AA0010 (Child), AB0001-AB0015 (Adult), AD0001-AD0002, PR0001-PR0003";

    show(null);
  },
};
