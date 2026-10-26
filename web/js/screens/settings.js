// Settings. Three option panels (LentOption, UserOption, BookOption) are shown alone in
// their own dialogs (대출환경설정, 회원등급설정, 도서관리설정) and together as tabs of
// 환경설정 (OptionDlg). 독서통장 isn't used, so its panel and 환경설정 tab are left out. Each panel's init returns { save() }, which
// checks the input with CLIB's messages and writes window.CLIB.library.settings.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};

(function () {
  const options = (select, values) => select.replaceChildren(...values.map((v, i) =>
    Object.assign(document.createElement("option"), { value: i, textContent: v })));
  // KeyPress handlers in CLIB only let digits through
  const digitsOnly = input => input.addEventListener("input", () => { input.value = input.value.replace(/\D/g, ""); });
  const int = v => parseInt(v, 10) || 0;
  // saveSettings answers { error } when it can't save (the read-only server)
  const saved = (ctx, result) => {
    if (result && result.error) { ctx.msgBox(result.error); return false; }
    return true;
  };

  // ---- 대출환경설정 (LentOption.cs) ---------------------------------------

  window.CLIB_LOGIC.LentOption = {
    server: true,
    lists: { dataGridView1: { editable: ["lendDays", "maxLend", "maxReserve"] } },
    columns: { dataGridView1: "equal" },
    init(ctx) {
      const lib = ctx.library;
      const $ = ctx.input;
      const L = lib.settings.lend;
      const grid = ctx.list("dataGridView1");
      // The designer text has a typo that CLIB shows corrected
      ctx.box("chk_attach").lastChild.textContent = "딸림자료 대출관리";

      const rows = lib.settings.grades.map(g => ({ userGrade: g.name, code: g.code,
        lendDays: String(g.lendDays), maxLend: String(g.maxLend), maxReserve: String(g.maxReserve) }));
      grid.setRows(rows);
      grid.onRowClick(() => {});

      $("check_LentDate").checked = L.includeLentDay;
      $("chk_attach").checked = L.attach;
      $("chk_relent").checked = L.relentConfirm;
      $("chk_relent_enable").checked = L.relentBan;
      $("txt_relentDay").value = L.relentDays;
      $("txt_DelayCharge").value = L.delayCharge;
      $("txt_DelayChargeMax").value = L.delayChargeMax;
      $("check_DelayLent").checked = L.delayLent;
      $("check_Charge").checked = L.chargeSuspend;
      $("txt_Extend").value = L.extendDays;
      $("txt_ExtendMax").value = L.extendMax;
      $("txt_Reserve").value = L.reserveDays;
      $("txt_ReserveMax").value = L.reserveMax;
      // The combos keep CLIB's items but hold their index as the value (SelectedIndex)
      const picked = { combo_Delay: L.delay, combo_Delay2: L.delayBasis, combo_Extend: L.extend, combo_Reserve: L.reserve };
      for (const [n, index] of Object.entries(picked)) {
        options($(n), [...$(n).options].map(o => o.textContent));
        $(n).value = index;
      }
      ["txt_relentDay", "txt_DelayCharge", "txt_DelayChargeMax", "txt_Extend", "txt_ExtendMax", "txt_Reserve", "txt_ReserveMax"]
        .forEach(n => digitsOnly($(n)));

      // CheckReLent(), SwitchDelayCombo(), SwitchExtendCombo(), SwitchReserveCombo()
      const show = (names, on) => names.forEach(n => { ctx.box(n).hidden = !on; });
      function sync() {
        $("txt_relentDay").disabled = !$("chk_relent_enable").checked;
        const delay = int($("combo_Delay").value);
        show(["combo_Delay2"], delay === 1);
        show(["label1", "label2", "label3", "txt_DelayCharge", "txt_DelayChargeMax"], delay === 2);
        $("check_Charge").disabled = delay !== 2;
        const extend = int($("combo_Extend").value);
        show(["label4", "label5", "label6", "txt_Extend", "txt_ExtendMax"], extend !== 0);
        ctx.box("label6").textContent = extend === 2 ? "1회 연장일" : "대출일 X ";
        show(["label7", "label8", "label9", "txt_Reserve", "txt_ReserveMax"], int($("combo_Reserve").value) !== 0);
      }
      ["chk_relent_enable", "combo_Delay", "combo_Extend", "combo_Reserve"].forEach(n => $(n).addEventListener("change", sync));
      sync();

      ctx.dialogButton("btn_RestDate", "RestDateDlg");
      ctx.notPorted("btn_LentDate_Batch");

      return {
        async save() {
          if (!rows.length) { ctx.msgBox("회원등급이 없습니다."); return false; }
          if (!saved(ctx, await lib.saveSettings({
            grades: lib.settings.grades.map(g => {
              const r = rows.find(x => x.code === g.code);
              return r ? { ...g, lendDays: int(r.lendDays), maxLend: int(r.maxLend), maxReserve: int(r.maxReserve) } : g;
            }),
            lend: {
              includeLentDay: $("check_LentDate").checked, attach: $("chk_attach").checked,
              relentConfirm: $("chk_relent").checked, relentBan: $("chk_relent_enable").checked,
              relentDays: int($("txt_relentDay").value) || 1,
              delay: int($("combo_Delay").value), delayBasis: int($("combo_Delay2").value),
              delayCharge: int($("txt_DelayCharge").value), delayChargeMax: int($("txt_DelayChargeMax").value),
              delayLent: $("check_DelayLent").checked, chargeSuspend: $("check_Charge").checked,
              extend: int($("combo_Extend").value), extendDays: int($("txt_Extend").value), extendMax: int($("txt_ExtendMax").value),
              reserve: int($("combo_Reserve").value), reserveDays: int($("txt_Reserve").value), reserveMax: int($("txt_ReserveMax").value),
            },
          }))) return false;
          return true;
        },
      };
    },
  };

  // ---- 회원등급설정 (UserOption.cs) ----------------------------------------

  window.CLIB_LOGIC.UserOption = {
    server: true,
    lists: { dataGridView1: { editable: ["gradeName", "prefix"] } },
    columns: { dataGridView1: "equal" },
    init(ctx) {
      const lib = ctx.library;
      const $ = ctx.input;
      const grid = ctx.list("dataGridView1");
      let rows = lib.settings.grades.map(g => ({ gradeCode: String(g.code), gradeName: g.name, prefix: g.prefix }));
      grid.setRows(rows);
      grid.onRowClick(() => {});
      $(lib.settings.userCodeByGrade ? "radioButton1" : "radioButton2").checked = true;

      $("btn_Add").addEventListener("click", () => {
        const code = Math.max(-1, ...rows.map(r => int(r.gradeCode))) + 1;
        rows.push({ gradeCode: String(code), gradeName: "", prefix: "" });
        grid.setRows(rows);
        grid.select(rows[rows.length - 1]);
      });
      $("btn_Delete").addEventListener("click", () => {
        const r = grid.selected();
        if (!r) return;
        if (rows.length <= 1) return ctx.msgBox("회원등급은 최소 1개 이상 사용하여야 합니다.");
        rows = rows.filter(x => x !== r);
        grid.setRows(rows);
      });

      return {
        async save() {
          const byGrade = $("radioButton1").checked;
          if (!rows.length) { ctx.msgBox("최소 1개 이상의 회원등급을 입력하여야 합니다."); return false; }
          if (rows.some(r => !r.gradeName.trim())) { ctx.msgBox("회원등급명을 입력해주세요."); return false; }
          if (byGrade && rows.some(r => !r.prefix.trim())) { ctx.msgBox("구분기호를 입력해주세요."); return false; }
          if (new Set(rows.map(r => r.gradeName.trim())).size !== rows.length) {
            ctx.msgBox("같은 회원등급명은 1개만 사용할 수 있습니다.");
            return false;
          }
          // Keep each grade's loan limits (edited in 대출환경설정); new grades copy the first one's
          const old = lib.settings.grades;
          if (!saved(ctx, await lib.saveSettings({
            userCodeByGrade: byGrade,
            grades: rows.map(r => {
              const prev = old.find(g => String(g.code) === r.gradeCode);
              // A new grade starts with CLIB's defaults: 5 books, 7 days, 3 reservations
              const limits = prev || { lendDays: 7, maxLend: 5, maxReserve: 3 };
              return { ...limits, code: int(r.gradeCode), name: r.gradeName.trim(), prefix: r.prefix.trim().toUpperCase() };
            }),
          }))) return false;
          return true;
        },
      };
    },
  };

  // ---- 도서관리설정 (BookOption.cs) ----------------------------------------

  window.CLIB_LOGIC.BookOption = {
    server: true,
    lists: { dataGridView1: { editable: ["location"] } },
    columns: { dataGridView1: "equal" },
    init(ctx) {
      const lib = ctx.library;
      const $ = ctx.input;
      const B = lib.settings.book;
      const A = B.authorCode;
      const grid = ctx.list("dataGridView1");

      options($("combo_AuthorCode"), window.CLIB.authorCode.TABLES);
      $("combo_AuthorCode").value = A.table;
      $(A.authorInitial ? "radio_Author2" : "radio_Author1").checked = true;
      $(A.titleInitial ? "radio_Book2" : "radio_Book1").checked = true;
      $(A.moum ? "radio_Moum2" : "radio_Moum1").checked = true;
      $(B.useSeriesTitle ? "radio_Total1" : "radio_Total2").checked = true;
      $(B.showPublisher ? "radio_Publish1" : "radio_Publish2").checked = true;
      $(B.isbnSearch ? "radio_isbn2" : "radio_isbn1").checked = true;

      let rows = B.locations.map(l => ({ code: String(l.code), location: l.name }));
      grid.setRows(rows);
      grid.onRowClick(() => {});
      $("btn_Add").addEventListener("click", () => {
        rows.push({ code: String(Math.max(0, ...rows.map(r => int(r.code))) + 1), location: "" });
        grid.setRows(rows);
        grid.select(rows[rows.length - 1]);
      });
      $("btn_Delete").addEventListener("click", () => {
        const r = grid.selected();
        if (!r) return;
        if (rows.length <= 1) return ctx.msgBox("최소 1개 이상의 소장위치를 입력하여야 합니다.");
        rows = rows.filter(x => x !== r);
        grid.setRows(rows);
      });

      return {
        async save() {
          const locations = rows.filter(r => r.location.trim()).map(r => ({ code: int(r.code), name: r.location.trim() }));
          if (!locations.length) { ctx.msgBox("최소 1개 이상의 소장위치를 입력하여야 합니다."); return false; }
          if (!saved(ctx, await lib.saveSettings({
            book: {
              authorCode: { table: int($("combo_AuthorCode").value), authorInitial: $("radio_Author2").checked,
                titleInitial: $("radio_Book2").checked, moum: $("radio_Moum2").checked },
              useSeriesTitle: $("radio_Total1").checked, showPublisher: $("radio_Publish1").checked,
              isbnSearch: $("radio_isbn2").checked ? 1 : 0, locations,
            },
          }))) return false;
          return true;
        },
      };
    },
  };

  // ---- the dialogs that show one panel ------------------------------------

  // panel1 hosts the option panel; 저장 saves it and closes, 취소 closes
  function single(panel, saveBtn, cancelBtn) {
    return {
      ownClose: true,
      server: true,
      init(ctx) {
        const api = ctx.embed(ctx.box("panel1"), panel);
        ctx.input(saveBtn).addEventListener("click", async () => { if (await api.save()) ctx.close(); });
        ctx.input(cancelBtn).addEventListener("click", () => ctx.close());
      },
    };
  }
  window.CLIB_LOGIC.LentOptionDlg = single("LentOption", "btn_save", "btn_cancle");
  window.CLIB_LOGIC.UserOptionDlg = single("UserOption", "btn_Save", "btn_Cancle");
  window.CLIB_LOGIC.BookOptionDlg = single("BookOption", "btn_save", "btn_cancle");

  // ---- 환경설정 (OptionDlg.cs) ----------------------------------------------

  window.CLIB_LOGIC.OptionDlg = {
    server: true,
    ownClose: true,
    init(ctx) {
      const lib = ctx.library;
      const $ = ctx.input;
      const LIB = lib.settings.library;
      $("txt_library").value = LIB.name;
      $("txt_phone").value = LIB.phone;
      $("txt_address").value = LIB.address;
      $("txt_email").value = LIB.email;

      // The other tabs hold the option panels in the middle column of a TableLayoutPanel
      const panels = [["tableLayoutPanel1", "LentOption"], ["tableLayoutPanel2", "UserOption"],
        ["tableLayoutPanel3", "BookOption"]];
      // 독서통장 설정 (tabPage6): its tab and page
      ctx.box("tabControl1").querySelectorAll(`[id$="-tabPage6"], [aria-controls$="-tabPage6"]`).forEach(el => el.remove());
      const apis = panels.map(([host, panel]) => {
        const box = ctx.box(host);
        box.classList.add("option-host");
        const api = ctx.embed(box, panel);
        Object.assign(box.lastElementChild.style, { left: "50%", right: "auto",
          width: `${window.CLIB_FORMS[panel].w}px`, transform: "translateX(-50%)" });
        return api;
      });

      // The panels are taller than the tab pages (대출환경설정 is 595px in a 574px page), which
      // would scroll; make the pages fit the tallest panel and move 저장/취소 below the tabs
      const tallest = Math.max(...panels.map(([, panel]) => window.CLIB_FORMS[panel].h));
      const tabs = ctx.box("tabControl1");
      const pages = [...tabs.querySelectorAll(".tab-page")];
      const pageTop = parseInt(pages[0].style.top, 10);
      const pageHeight = tallest + 10;
      pages.forEach(p => { p.style.height = `${pageHeight}px`; });
      panels.forEach(([host]) => { ctx.box(host).style.height = `${tallest + 4}px`; });
      tabs.style.height = `${pageTop + pageHeight + 2}px`;
      const below = tabs.offsetTop + pageTop + pageHeight + 12;
      ["btn_save", "btn_cancle"].forEach(n => { ctx.box(n).style.top = `${below}px`; });

      ctx.notPorted("btn_password");
      $("btn_save").addEventListener("click", async () => {
        // Save every tab in turn; stop at the first one whose input CLIB would reject
        for (const api of apis) if (!await api.save()) return;
        if (!saved(ctx, await lib.saveSettings({ library: { name: $("txt_library").value.trim(), phone: $("txt_phone").value.trim(),
          address: $("txt_address").value.trim(), email: $("txt_email").value.trim() } }))) return false;
        ctx.close();
      });
      $("btn_cancle").addEventListener("click", () => ctx.close());
    },
  };
})();
