// Starting and stopping (server/app.py run_sequence), not CLIB forms:
// - while the server backs up and downloads from the cloud as it starts, a banner over the
//   workspace shows how far it is
// - 종료 backs up, uploads to the cloud and stops the server
(function () {
  const api = path => new URL(`api/${path}`, location.href);
  const STEPS = { backup: "데이터 백업", download: "클라우드 다운로드", upload: "클라우드 업로드" };

  async function sequence() {
    const res = await fetch(api("sequence"));
    if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
    return res.json();
  }

  // ---- the start banner ---------------------------------------------------

  async function watchStart() {
    let s;
    try {
      s = await sequence();
    } catch (e) {
      return;  // opened from disk, or an older server
    }
    if (s.kind !== "start" || (s.state !== "running" && s.state !== "error")) return;
    const msg = document.createElement("span");
    msg.className = "msg";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "btn";
    close.textContent = "닫기";
    const banner = document.createElement("div");
    banner.className = "session-banner";
    banner.setAttribute("role", "status");
    banner.append(msg, close);
    close.addEventListener("click", () => banner.remove());
    document.querySelector("#workspace").before(banner);

    while (banner.isConnected) {
      if (s.state === "running") {
        msg.textContent = `시작 준비 중: ${STEPS[s.step] || ""}${s.phase ? ` (${s.phase})` : ""}… ` +
          "끝날 때까지 대출·반납을 하지 마세요.";
      } else if (s.state === "error") {
        banner.classList.add("error");
        msg.textContent = `시작 준비 중 문제가 생겼습니다.\n${s.error || ""}`;
        return;
      } else {
        banner.classList.add("done");
        msg.textContent = `시작 준비를 마쳤습니다. 백업 ${s.backup || ""}${s.skipped ? ` · ${s.skipped}` : " · 클라우드 다운로드 완료"}. ` +
          "열려 있던 화면은 다시 열어야 새 자료가 보입니다.";
        setTimeout(() => banner.remove(), 15000);
        return;
      }
      await new Promise(r => setTimeout(r, 1500));
      try {
        s = await sequence();
      } catch (e) {
        msg.textContent = `서버와 연결이 끊겼습니다. ${e.message}`;
        return;
      }
    }
  }
  if (location.protocol.startsWith("http")) watchStart();

  // ---- 종료 ------------------------------------------------------------------

  window.CLIB_FORMS = window.CLIB_FORMS || {};
  window.CLIB_FORMS.Shutdown = {
    title: "종료", w: 460, h: 236, backColor: null, bold: false,
    children: [
      { id: "label_info", type: "label", x: 14, y: 12, w: 432, h: 34, align: "left", valign: "middle",
        text: "데이터를 백업하고 클라우드에 업로드한 뒤 서버를 종료합니다." },
      { id: "label_backup", type: "label", x: 24, y: 56, w: 420, h: 22, align: "left", valign: "middle", text: "" },
      { id: "label_upload", type: "label", x: 24, y: 80, w: 420, h: 22, align: "left", valign: "middle", text: "" },
      { id: "label_stop", type: "label", x: 24, y: 104, w: 420, h: 22, align: "left", valign: "middle", text: "" },
      { id: "label_phase", type: "label", x: 14, y: 132, w: 432, h: 44, align: "left", valign: "top", text: "", bold: true },
      { id: "btn_run", type: "button", x: 156, y: 188, w: 140, h: 32, text: "종료", bold: true },
      { id: "btn_close", type: "button", x: 306, y: 188, w: 140, h: 32, text: "닫기", bold: true },
    ],
  };

  window.CLIB_LOGIC = window.CLIB_LOGIC || {};
  window.CLIB_LOGIC.Shutdown = {
    ownClose: true,
    server: true,
    init(ctx) {
      const $ = ctx.input;
      const phase = ctx.box("label_phase");
      phase.style.whiteSpace = "pre-line";
      let timer = null;
      let requested = false;  // 종료 pressed in this dialog

      // ✔ done, ▶ now, ✖ failed, · not yet
      function steps(s) {
        const stop = s && s.kind === "stop" ? s : null;
        const order = ["backup", "upload", "stop"];
        const at = !stop ? -1 : stop.state === "stopped" ? 3 : stop.state === "done" ? 2 : order.indexOf(stop.step);
        const mark = i => !stop || at < i ? "·" : at > i ? "✔" : stop.state === "error" ? "✖" : "▶";
        ctx.box("label_backup").textContent = `${mark(0)}  1. 데이터 백업${stop && stop.backup ? ` (${stop.backup})` : ""}`;
        ctx.box("label_upload").textContent = `${mark(1)}  2. 클라우드 업로드`;
        ctx.box("label_stop").textContent = `${mark(2)}  3. 서버 종료`;
      }

      function render(s) {
        steps(s);
        const running = s.state === "running";
        $("btn_run").disabled = running || s.state === "stopped" || !s.canStop || !ctx.library.isServer;
        if (!s.canStop) phase.textContent = "이 서버는 화면에서 종료할 수 없습니다. (run.bat으로 실행된 서버가 아닙니다)";
        else if (running) phase.textContent = s.kind === "start"
          ? "시작 준비(백업, 클라우드 다운로드)가 진행중입니다. 끝난 뒤에 종료해주세요."
          : `${STEPS[s.step] || ""} 중…${s.phase ? ` (${s.phase})` : ""}`;
        else if (s.state === "stopped") phase.textContent = "서버를 종료했습니다. 브라우저를 닫아도 됩니다.";
        else if (s.state === "error" && s.kind === "stop") phase.textContent = `종료하지 못했습니다. 서버는 계속 실행 중입니다.\n${s.error || ""}`;
        else phase.textContent = "";
      }

      async function watch() {
        clearTimeout(timer);
        if (!phase.isConnected) return;
        let s;
        try {
          s = await sequence();
        } catch (e) {
          // After the last step the server is gone; before it, the connection really failed
          if (requested) {
            render({ kind: "stop", state: "stopped", canStop: true });
            return;
          }
          phase.textContent = `서버와 연결하지 못했습니다. ${e.message}`;
          return;
        }
        render(s);
        if (s.state === "running" || (requested && s.state === "done")) timer = setTimeout(watch, 1000);
        else if (requested && s.state === "error") ctx.msgBox(phase.textContent);
      }

      $("btn_run").addEventListener("click", async () => {
        if (!await ctx.confirm("데이터를 백업하고 클라우드에 업로드한 뒤 서버를 종료합니다.\n종료하시겠습니까?", "종료")) return;
        const res = await fetch(api("shutdown"), { method: "POST" });
        const result = await res.json();
        if (result.error) return ctx.msgBox(result.error);
        requested = true;
        watch();
      });
      $("btn_close").addEventListener("click", () => { clearTimeout(timer); ctx.close(); });

      steps(null);
      if (!ctx.library.isServer) {
        $("btn_run").disabled = true;
        phase.textContent = "서버에 연결된 경우에만 사용할 수 있습니다.";
        return;
      }
      setTimeout(watch);  // init runs before the dialog is on the page
    },
  };
})();
