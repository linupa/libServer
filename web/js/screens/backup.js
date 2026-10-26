// 데이터베이스 관리: 데이터백업 (BookDream.DataBackUp), 데이터복구 (DataRestore.exe) and
// 자동백업설정 (Set_Backup). The backups are SQL Server .bak files that LocalDB writes on the
// server's PC (server/backup.py), the same kind CLIB makes, so either program can restore them.
// 데이터백업 has no form in CLIB (only a save dialog), and DataRestore is a separate program,
// so their layouts are written here in the shape the extractor produces.
(function () {
  window.CLIB_FORMS = window.CLIB_FORMS || {};
  window.CLIB_LOGIC = window.CLIB_LOGIC || {};
  const NEEDS_SERVER = "데이터 백업과 복구는 서버(server\\run.bat)에 연결된 경우에만 사용할 수 있습니다.";
  const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const mb = n => `${(n / 1048576).toFixed(1)} MB`;

  // Without the server there is no database to back up
  function serverOnly(ctx) {
    if (ctx.library.isServer) return true;
    ctx.close();
    ctx.msgBox(NEEDS_SERVER);
    return false;
  }
  function download(url) {
    const a = Object.assign(document.createElement("a"), { href: url, download: "" });
    document.body.append(a);
    a.click();
    a.remove();
  }

  // ---- 데이터백업 -----------------------------------------------------------------
  window.CLIB_FORMS.DataBackup = {
    title: "데이터백업", w: 600, h: 380, backColor: null, bold: false,
    children: [
      { id: "label_info", type: "label", x: 14, y: 10, w: 572, h: 40, align: "left", valign: "middle", text: "" },
      { id: "panel_table", type: "panel", x: 14, y: 56, w: 572, h: 262, back: "white" },
      { id: "label_phase", type: "label", x: 14, y: 330, w: 260, h: 32, align: "left", valign: "middle", text: "", bold: true },
      { id: "btn_backup", type: "button", x: 286, y: 330, w: 150, h: 32, text: "백업하기", bold: true },
      { id: "btn_close", type: "button", x: 446, y: 330, w: 140, h: 32, text: "닫기", bold: true },
    ],
  };
  window.CLIB_LOGIC.DataBackup = {
    server: true,
    ownClose: true,

    init(ctx) {
      if (!serverOnly(ctx)) return;
      const lib = ctx.library;
      const $ = ctx.input;
      const table = ctx.box("panel_table");
      table.style.overflow = "auto";
      // The folder path can be long: let the line wrap inside its box
      Object.assign(ctx.box("label_info").style, { whiteSpace: "pre-line", lineHeight: "18px", overflowWrap: "anywhere" });
      $("btn_close").addEventListener("click", () => ctx.close());

      async function refresh() {
        const info = await lib.backups();
        ctx.box("label_info").textContent =
          `현재 데이터(${info.database})를 백업 파일(.bak)로 저장하고 내 컴퓨터로도 내려받습니다.\n저장 위치: ${info.folders.backup}`;
        table.innerHTML = `<table class="cloud-table"><thead><tr><th>위치</th><th>파일</th><th>크기</th><th>날짜</th><th></th></tr></thead><tbody>${
          info.files.map(f => `<tr><td>${esc(f.place)}</td><td>${esc(f.name)}</td><td class="num">${mb(f.size)}</td><td>${esc(f.time)}</td>` +
            `<td><a href="${esc(lib.backupFileUrl(f.folder, f.name))}" download>내려받기</a></td></tr>`).join("") ||
          '<tr><td colspan="5">백업 파일이 없습니다.</td></tr>'}</tbody></table>`;
      }

      // backgroundWorker1: "백업중.." until BACKUP DATABASE is done, then "백업 완료"
      $("btn_backup").addEventListener("click", async () => {
        $("btn_backup").disabled = true;
        ctx.box("label_phase").textContent = "백업중..";
        try {
          const result = await lib.backup();
          if (result.error) return ctx.msgBox(result.error);
          await refresh();
          // CLIB asks where to save the file; here it is also kept on the server
          download(lib.backupFileUrl(result.folder, result.name));
          ctx.box("label_phase").textContent = "";
          await ctx.msgBox(`백업 완료\n${result.name} (${mb(result.size)})`);
        } finally {
          $("btn_backup").disabled = false;
          ctx.box("label_phase").textContent = "";
        }
      });
      refresh();
    },
  };

  // ---- 데이터복구 (DataRestore.exe: 556 x 226, bold 11pt) ---------------------------
  // textBox1 (the chosen file) is a list of the backups on the server; 파일선택 sends a .bak
  // from this computer to the server and selects it
  window.CLIB_FORMS.DataRestore = {
    title: "데이터 복구", w: 556, h: 226, backColor: null, bold: true,
    children: [
      { id: "label1", type: "label", x: 18, y: 23, w: 109, h: 15, text: "복구파일 선택", bold: true },
      { id: "combo_file", type: "combo", x: 137, y: 18, w: 290, h: 24, items: [], dropDownList: true },
      { id: "button1", type: "button", x: 435, y: 17, w: 96, h: 26, text: "파일선택", bold: true },
      { id: "label2", type: "label", x: 24, y: 57, w: 346, h: 15, text: "※ 복구가 진행되면 현재 데이터는 삭제됩니다.", fore: "red", bold: true },
      { id: "label3", type: "label", x: 44, y: 78, w: 341, h: 15, text: "복구전 데이터를 미리 백업해두시기 바랍니다.", fore: "red", bold: true },
      { id: "label4", type: "label", x: 24, y: 102, w: 464, h: 15, text: "※ 복구가 진행되는 중에 프로그램을 비정상적으로 종료할 경우", fore: "red", bold: true },
      { id: "label5", type: "label", x: 44, y: 126, w: 223, h: 15, text: "데이터가 손상될 수 있습니다.", fore: "red", bold: true },
      { id: "button2", type: "button", x: 88, y: 163, w: 137, h: 41, text: "복구하기", bold: true },
      { id: "button3", type: "button", x: 335, y: 163, w: 137, h: 41, text: "취소", bold: true },
    ],
  };
  window.CLIB_LOGIC.DataRestore = {
    server: true,
    ownClose: true,

    init(ctx) {
      if (!serverOnly(ctx)) return;
      const lib = ctx.library;
      const $ = ctx.input;
      let files = [];
      const busy = on => ["combo_file", "button1", "button2", "button3"].forEach(n => { $(n).disabled = on; });

      async function refresh(select) {
        files = (await lib.backups()).files;
        $("combo_file").replaceChildren(...files.map((f, i) => Object.assign(document.createElement("option"), {
          value: String(i), textContent: `${f.name} (${f.place}, ${f.time.slice(0, 16)})` })));
        const at = select ? files.findIndex(f => f.folder === select.folder && f.name === select.name) : 0;
        if (at >= 0 && files.length) $("combo_file").value = String(at);
      }

      // 파일선택: a .bak from this computer
      const picker = Object.assign(document.createElement("input"), { type: "file", accept: ".bak", hidden: true });
      ctx.box("button1").after(picker);
      $("button1").addEventListener("click", () => picker.click());
      picker.addEventListener("change", async () => {
        const file = picker.files[0];
        picker.value = "";
        if (!file) return;
        busy(true);
        $("button1").textContent = "올리는 중…";
        try {
          const result = await lib.uploadBackup(file);
          if (result.error) return ctx.msgBox(result.error);
          await refresh(result);
        } finally {
          $("button1").textContent = "파일선택";
          busy(false);
        }
      });

      $("button3").addEventListener("click", () => ctx.close());
      $("button2").addEventListener("click", async () => {
        const f = files[Number($("combo_file").value)];
        if (!f) return ctx.msgBox("복구할 백업 파일을 선택해주세요.");
        // DataRestore(): CLIB closes itself first; here every connection to the data is cut off
        if (!await ctx.confirm(`${f.name} 파일로 데이터를 복구합니다.\n` +
          "복구하는 동안 CLIB, 키오스크 등 이 데이터를 쓰는 프로그램의 연결이 끊어집니다.\n계속하시겠습니까?\n" +
          "※저장하지 않은 데이터는 모두 삭제되오니 주의해주시기 바랍니다.", "데이터 복구")) return;
        busy(true);
        $("button2").textContent = "복구중..";
        try {
          const result = await lib.restoreBackup(f.folder, f.name);
          if (result.error) return ctx.msgBox(result.error, "데이터 복구");
          await ctx.msgBox(`데이터 복구가 완료되었습니다.\n복구 전 데이터는 ${result.before} 파일로 백업되었습니다.\n\n화면을 다시 불러옵니다.`, "복구완료");
          // Every screen and setting comes from the restored data
          location.hash = "";
          location.reload();
        } finally {
          $("button2").textContent = "복구하기";
          busy(false);
        }
      });
      refresh();
    },
  };

  // ---- 자동백업설정 (Set_Backup) ------------------------------------------------------
  window.CLIB_LOGIC.Set_Backup = {
    server: true,
    ownClose: true, // 확인 / 취소

    init(ctx) {
      if (!serverOnly(ctx)) return;
      const lib = ctx.library;
      const $ = ctx.input;
      // 위치찾기 browses folders on CLIB's PC; a web page can't, so the path is typed instead
      $("txt_folder").readOnly = false;
      $("txt_folder").classList.remove("ro");
      $("btn_folder").disabled = true;
      $("btn_folder").title = "서버 PC의 폴더 경로를 직접 입력하세요.";

      // SwitchCheck(): the options only apply with 자동백업 on
      const sync = () => ["txt_date", "comboBox1"].forEach(n => { $(n).disabled = !$("checkBox1").checked; });
      $("checkBox1").addEventListener("change", sync);
      lib.backups().then(({ options, runs }) => {
        $("checkBox1").checked = options.auto;
        $("txt_folder").value = options.path;
        $("txt_date").value = options.days;
        $("comboBox1").value = runs[options.run];
        if (options.last) $("checkBox1").parentElement.title = `마지막 자동백업: ${options.last}`;
        sync();
      });

      $("btn_cancle").addEventListener("click", () => ctx.close());
      $("btn_ok").addEventListener("click", async () => {
        $("btn_ok").disabled = true;
        try {
          const items = [...$("comboBox1").options].map(o => o.value);
          const result = await lib.saveBackupOptions({ auto: $("checkBox1").checked, path: $("txt_folder").value,
            days: $("txt_date").value, run: items.indexOf($("comboBox1").value) });
          if (result.error) return ctx.msgBox(result.error);
          ctx.close();
        } finally {
          $("btn_ok").disabled = false;
        }
      });
    },
  };
})();
