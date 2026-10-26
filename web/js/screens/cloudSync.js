// 클라우드 다운로드 / 업로드: keep this server's database and the cloud's in step
// (server/cloud.py, after libServer's downloadDB.py and uploadDB.py). These aren't CLIB forms,
// so their layout is written here in the shape the extractor produces. The work runs on the
// server, one job at a time; the dialog polls its progress.
(function () {
  const ROWS = [["book", "도서"], ["marc", "MARC"], ["user", "회원"], ["rentHistory", "대출기록"], ["rent", "대출현황"]];
  const MODES = {
    download: {
      id: "CloudDownload", title: "클라우드 다운로드", verb: "다운로드",
      info: "클라우드의 자료로 이 서버의 데이터베이스(CLIB와 함께 쓰는 자료)를 맞춥니다.",
      source: ["클라우드", "count"], fetched: ["받음", "downloaded"],
      ask: "이 서버의 도서, MARC, 회원, 대출 자료를 클라우드의 자료로 바꿉니다.\n클라우드에 없는 자료는 삭제됩니다.\n다운로드하시겠습니까?",
    },
    upload: {
      id: "CloudUpload", title: "클라우드 업로드", verb: "업로드",
      info: "이 서버의 자료로 클라우드를 맞춥니다. 회원의 전화번호와 이메일은 서명값도 함께 올립니다.",
      source: ["로컬", "local"], fetched: ["클라우드", "downloaded"],
      ask: "클라우드의 도서, MARC, 회원, 대출 자료를 이 서버의 자료로 바꿉니다.\n이 서버에 없는 자료는 클라우드에서 삭제됩니다.\n업로드하시겠습니까?",
    },
  };

  window.CLIB_FORMS = window.CLIB_FORMS || {};
  window.CLIB_LOGIC = window.CLIB_LOGIC || {};
  for (const [mode, m] of Object.entries(MODES)) {
    window.CLIB_FORMS[m.id] = {
      title: m.title, w: 600, h: 340, backColor: null, bold: false,
      children: [
        { id: "label_info", type: "label", x: 14, y: 12, w: 572, h: 36, align: "left", valign: "middle", text: m.info },
        { id: "panel_table", type: "panel", x: 14, y: 52, w: 572, h: 186, back: "white" },
        { id: "label_phase", type: "label", x: 14, y: 246, w: 572, h: 22, align: "left", valign: "middle", text: "", bold: true },
        { id: "btn_test", type: "button", x: 14, y: 288, w: 150, h: 32, text: "비교만 하기", bold: true },
        ...(mode === "upload" ? [{ id: "check_bookOnly", type: "check", x: 176, y: 294, w: 104, h: 20, text: "도서·MARC만" }] : []),
        { id: "btn_run", type: "button", x: 286, y: 288, w: 150, h: 32, text: m.verb, bold: true },
        { id: "btn_close", type: "button", x: 446, y: 288, w: 140, h: 32, text: "닫기", bold: true },
      ],
    };
    window.CLIB_LOGIC[m.id] = { ownClose: true, server: true, init: ctx => init(ctx, mode, m) };
  }

  const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const api = path => new URL(`api/${path}`, location.href);

  function init(ctx, mode, m) {
    const $ = ctx.input;
    const table = ctx.box("panel_table");
    const phase = ctx.box("label_phase");
    let timer = null;
    let started = false;  // tell the result only for a run started from this dialog

    function render(s) {
      // A job in the other direction is reported in words, not in these columns
      const mine = s && s.mode === mode;
      const t = (mine && s.tables) || {};
      const cell = v => `<td class="num">${v === undefined || v === null ? "" : esc(v)}</td>`;
      table.innerHTML = `<table class="cloud-table"><thead><tr><th>자료</th><th>${m.source[0]}</th><th>${m.fetched[0]}</th>
        <th>추가</th><th>변경</th><th>삭제</th><th>적용</th></tr></thead><tbody>${ROWS.map(([k, label]) => {
          const r = t[k] || {};
          const extra = r.appended ? ` <small>(+${esc(r.appended)} rentHistory)</small>` : "";
          return `<tr><td>${label}${extra}</td>${cell(r[m.source[1]])}${cell(r[m.fetched[1]])}${cell(r.add)}${cell(r.change)}${
            cell(r.delete)}${cell(r.applied === undefined ? "" : `${r.applied}%`)}</tr>`;
        }).join("")}</tbody></table>`;
      const running = s && s.state === "running";
      const other = s && s.mode && s.mode !== mode ? MODES[s.mode].verb : null;
      phase.textContent = !s || s.state === "idle" ? ""
        : running ? (other ? `클라우드 ${other}가 진행중입니다.` : `${s.test ? "비교" : m.verb}: ${s.phase || ""}`)
        : !mine ? ""
        : s.state === "error" ? "실패했습니다."
        : s.test ? "비교를 마쳤습니다. (바뀐 것은 없습니다)" : `${m.verb}를 마쳤습니다.`;
      ["btn_test", "btn_run"].forEach(n => { $(n).disabled = running || !ctx.library.isServer; });
    }

    async function watch() {
      clearTimeout(timer);
      if (!table.isConnected) return;
      const s = await (await fetch(api("cloud"))).json();
      render(s);
      if (s.state === "running") {
        timer = setTimeout(watch, 1000);
        return;
      }
      if (!started || s.mode !== mode) return;
      started = false;
      if (s.state === "error") return ctx.msgBox(s.error || `${m.verb}에 실패했습니다.`);
      const r = s.result || {};
      const lines = ROWS.filter(([k]) => r[k]).map(([k, label]) =>
        `${label} : 추가 ${r[k].add}, 변경 ${r[k].change}, 삭제 ${r[k].delete}${r[k].appended ? `, rentHistory 추가 ${r[k].appended}` : ""}`);
      await ctx.msgBox(`${s.test ? "비교 결과입니다. 아무것도 바뀌지 않았습니다." : `${m.verb}를 마쳤습니다.`}\n\n${lines.join("\n")}${
        s.warning ? `\n\n${s.warning}` : ""}`);
    }

    async function start(test) {
      if (!test && !await ctx.confirm(m.ask, m.title)) return;
      const bookOnly = mode === "upload" && $("check_bookOnly").checked;
      const res = await fetch(api(`cloud/${mode}`), {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ test, bookOnly }),
      });
      const result = await res.json();
      if (result.error) return ctx.msgBox(result.error);
      started = true;
      watch();
    }

    $("btn_test").addEventListener("click", () => start(true));
    $("btn_run").addEventListener("click", () => start(false));
    $("btn_close").addEventListener("click", () => { clearTimeout(timer); ctx.close(); });

    render(null);
    if (!ctx.library.isServer) {
      phase.textContent = "서버에 연결된 경우에만 사용할 수 있습니다.";
      return;
    }
    // A job started earlier (or from another window) is shown as it goes. init runs
    // before the dialog is on the page, so start once it is.
    setTimeout(watch);
  }
})();
