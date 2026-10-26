// CLIB_Self.exe (자가대출반납) on the web. Form1 shows one panel at a time: Home, LentBook,
// ReturnBook or SearchBook. Everything goes through the same /api as the library's app;
// lending and returning use its question/answer protocol, answered the way the kiosk works.
(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  // ---- API -------------------------------------------------------------------

  async function get(path, params) {
    const url = new URL(`api/${path}`, location.href);
    for (const [k, v] of Object.entries(params || {})) if (v) url.searchParams.set(k, v);
    const res = await fetch(url);
    if (res.status === 404) return null;
    const body = await res.json();
    if (!res.ok) throw new Error(body && body.error ? body.error : `서버 오류 (${res.status})`);
    return body;
  }
  async function post(path, body) {
    const res = await fetch(new URL(`api/${path}`, location.href), {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const result = await res.json();
    if (!res.ok && !(result && result.error)) throw new Error(`서버 오류 (${res.status})`);
    return result;
  }
  const findUser = id => get(`users/${encodeURIComponent(id)}`);

  // The desk's questions, answered as CLIB_Self behaves: it never asks about 재대출, lends
  // without the 딸림자료 and leaves it to the desk on return, and goes on when the borrower
  // can no longer be found. kiosk: books someone has reserved go back at the desk.
  const LEND_ANSWERS = { relend: true, attach: false, attachOut: true };
  const RETURN_ANSWERS = { kiosk: true, missingUser: true, attach: false };

  // ---- dialogs -----------------------------------------------------------------

  let closeDialogs = () => {};
  function dialog(html, setup) {
    return new Promise(resolve => {
      const box = document.createElement("div");
      box.className = "dlg";
      box.setAttribute("role", "dialog");
      box.setAttribute("aria-modal", "true");
      box.innerHTML = html;
      $("#dialogs").append(box);
      const done = value => { box.remove(); closeDialogs = () => {}; resolve(value); };
      closeDialogs = () => done(false);
      setup(box, done);
    });
  }
  // MessageBox.Show(text)
  const msg = text => dialog(`<div class="msg"><header>CLIB</header><p>${esc(text)}</p>
    <footer><button type="button">확인</button></footer></div>`, (box, done) => {
    const ok = $("button", box);
    ok.addEventListener("click", () => done(true));
    ok.focus();
  });
  async function messages(list) {
    for (const m of list || []) await msg(m);
  }
  // YesNoDlg: the details of a loan or return ("대출하시겠습니까?"), or the done notice
  // ("대출이 정상적으로 처리되었습니다.") asking whether to go on. Resolves true for 예.
  function yesNo(body) {
    return dialog(`<div class="yesno">${body}<div class="buttons">
      <button type="button" data-v="1">예</button><button type="button" data-v="0">아니오</button></div></div>`,
    (box, done) => {
      box.querySelectorAll("button").forEach(b => b.addEventListener("click", () => done(b.dataset.v === "1")));
      $("button", box).focus();
    });
  }
  // CLIB drops a bracketed part of the title, e.g. "(개정판)"
  const shortTitle = t => String(t || "").replace(/\([^)]*\)/, "").trim();
  const confirmDetails = (title, p) => yesNo(`<h2>${title}</h2><dl>
    <dt>대출자번호 :</dt><dd>${esc(p.userId)}</dd><dt>대출자명 :</dt><dd>${esc(p.userName)}</dd>
    <dt>도서번호 :</dt><dd>${esc(p.barcode)}</dd><dt>도서명 :</dt><dd>${esc(shortTitle(p.title))}</dd>
    <dt>대출일 :</dt><dd>${esc(p.lentDate)}</dd><dt>반납일 :</dt><dd>${esc(p.dueDate)}</dd></dl>`);
  const goOn = (done, question, hint) => yesNo(`<h2 class="lead">${done}</h2>
    <p class="lead2">${question}</p><p class="hint">${hint}</p>`);

  // ---- screens and the idle timer ------------------------------------------------

  // timer1: back to the menu after a minute without input (two on 도서검색)
  const IDLE = { lend: 60, return: 60, search: 120 };
  let current = "home";
  let idle = 0;
  const screens = {};
  function show(id) {
    closeDialogs();
    document.querySelectorAll(".screen").forEach(s => { s.hidden = s.id !== id; });
    current = id;
    idle = 0;
    if (screens[id]) screens[id].reset();
  }
  ["keydown", "pointerdown", "pointermove", "input"].forEach(type =>
    document.addEventListener(type, () => { idle = 0; }, true));
  setInterval(() => {
    if (IDLE[current] && ++idle >= IDLE[current]) show("home");
  }, 1000);
  document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => show(b.dataset.go)));
  document.querySelectorAll(".home").forEach(b => b.addEventListener("click", () => show("home")));

  // A DataGridView: columns [header, key, weight], rows of objects
  function grid(host, columns, rows, { onPick, sortable } = {}) {
    const total = columns.reduce((n, c) => n + c[2], 0);
    let sort = null;
    function render() {
      const list = sort ? [...rows].sort((a, b) => {
        const x = a[sort.key], y = b[sort.key];
        const n = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "ko", { numeric: true });
        return sort.dir * n;
      }) : rows;
      host.innerHTML = `<table><colgroup>${columns.map(c => `<col style="width:${(c[2] / total) * 100}%">`).join("")}</colgroup>
        <thead><tr>${columns.map(c => `<th class="${sortable ? "sortable" : ""}" data-k="${c[1]}"
          ${sort && sort.key === c[1] ? `aria-sort="${sort.dir > 0 ? "ascending" : "descending"}"` : ""}>${c[0]}</th>`).join("")}</tr></thead>
        <tbody>${list.map((r, i) => `<tr data-i="${rows.indexOf(r)}">${columns.map(c => `<td title="${esc(r[c[1]])}">${esc(r[c[1]])}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    }
    render();
    host.onclick = e => {
      const th = e.target.closest("th");
      if (th && sortable) {
        sort = { key: th.dataset.k, dir: sort && sort.key === th.dataset.k ? -sort.dir : 1 };
        return render();
      }
      const tr = e.target.closest("tbody tr");
      if (!tr) return;
      host.querySelectorAll("tr.selected").forEach(t => t.classList.remove("selected"));
      tr.classList.add("selected");
      if (onPick) onPick(rows[tr.dataset.i]);
    };
    return {
      select(key, value) {
        const i = rows.findIndex(r => r[key] === value);
        const tr = host.querySelector(`tbody tr[data-i="${i}"]`);
        if (tr) { tr.classList.add("selected"); tr.scrollIntoView({ block: "nearest" }); }
      },
    };
  }

  // ---- 대출 / 반납: the shared member panel and loan list ----------------------------

  const LOAN_COLUMNS = [["등록번호", "barcode", 2], ["도서명", "title", 5], ["도서상태", "state", 1],
    ["대출일", "lentDate", 1], ["반납일", "dueDate", 1]];
  function circulation(root) {
    const input = $(".code", root);
    const panel = $(".user", root);
    const list = $(".list", root);
    let user = null;
    const view = {
      get user() { return user; },
      input,
      focus() { input.focus(); input.select(); },
      clear() {
        user = null;
        input.value = "";
        panel.hidden = true;
        list.hidden = true;
        list.innerHTML = "";
      },
      // SelectUser(): the member's details and the books they have out
      async load(id, onPick) {
        const found = await findUser(id);
        if (!found) return null;
        user = found;
        const f = { userId: found.userId, userName: found.userName, lendDays: found.lendDays,
          maxLend: found.maxLend, lentCount: found.lentCount };
        panel.querySelectorAll("[data-f]").forEach(dd => { dd.textContent = f[dd.dataset.f] ?? ""; });
        panel.hidden = false;
        const rows = found.loans.map(l => ({ barcode: l.barcode,
          title: l.book.volume ? `${l.book.title}.${l.book.volume}` : l.book.title,
          state: l.state, lentDate: l.lentDate, dueDate: l.dueDate }));
        list.hidden = !rows.length;
        const g = grid(list, LOAN_COLUMNS, rows, { onPick });
        input.value = "";
        input.focus();
        return { user: found, grid: g };
      },
    };
    input.addEventListener("input", () => {
      const at = input.selectionStart;
      input.value = input.value.toUpperCase();
      input.setSelectionRange(at, at);
    });
    return view;
  }

  // ---- 대출 (LentBook) ---------------------------------------------------------------

  (function () {
    const root = $("#lend");
    const c = circulation(root);
    const info = $(".info", root);
    const info2 = $(".info2", root);
    let busy = false;

    function reset() {
      c.clear();
      info.textContent = "회원번호를 입력해주세요.";
      info2.hidden = true;
      setTimeout(() => c.focus());
    }
    screens.lend = { reset };

    async function selectUser(id) {
      const shown = await c.load(id);
      if (!shown) {
        await msg("조회된 회원이 없습니다.");
        return c.focus();
      }
      info.textContent = "도서번호를 스캐너로 읽거나 키보드로 입력해주세요.";
      info2.hidden = false;
      return shown;
    }

    async function lend() {
      const barcode = c.input.value.trim().toUpperCase();
      const user = c.user;
      if (!barcode) return msg("도서 등록번호를 입력해주세요.");
      if (user.lentCount >= user.maxLend) {
        await msg("최대 권수만큼 대출중입니다.\n대출도서를 반납 후 이용해주세요.");
        return c.focus();
      }
      const preview = await post("lend", { userId: user.userId, barcode, answers: { ...LEND_ANSWERS, preview: true } });
      if (preview.error || !preview.preview) {
        await msg(preview.error || "대출할 수 없는 도서입니다.");
        return c.focus();
      }
      if (!await confirmDetails("대출하시겠습니까?", preview.preview)) return c.focus();
      const result = await post("lend", { userId: user.userId, barcode, answers: LEND_ANSWERS });
      if (result.error || !result.ok) {
        await msg(result.error || "대출하지 못했습니다.");
        return c.focus();
      }
      const shown = await c.load(user.userId);
      if (shown) shown.grid.select("barcode", result.loan.barcode);
      if (!await goOn("대출이 정상적으로 처리되었습니다.", "다른 도서를 계속 대출하시겠습니까?",
        "(예 : 계속대출, 아니오 : 초기화면으로)")) return show("home");
      c.focus();
    }

    // EnterCode(): the first number is the member's, the next ones are books
    async function enter() {
      if (busy) return;
      const code = c.input.value.trim().toUpperCase();
      busy = true;
      try {
        if (c.user) await lend();
        else if (!code) await msg("회원번호를 입력해주세요.");
        else await selectUser(code);
      } catch (e) {
        await msg(e.message);
      } finally {
        busy = false;
      }
    }
    c.input.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) enter(); });
    $(".ok", root).addEventListener("click", () => { if (c.input.value.trim()) enter(); });
  })();

  // ---- 반납 (ReturnBook) ---------------------------------------------------------------

  (function () {
    const root = $("#return");
    const c = circulation(root);
    const info = $(".info", root);
    const ok = $(".ok", root);
    let busy = false;

    function reset() {
      c.clear();
      info.textContent = "회원번호를 입력하거나, 도서번호를 입력해주세요.";
      ok.textContent = "확인";
      setTimeout(() => c.focus());
    }
    screens.return = { reset };

    // Clicking a book in the list puts its number in the box
    const pick = row => { c.input.value = row.barcode; c.input.focus(); };
    async function selectUser(id) {
      const shown = await c.load(id, pick);
      if (!shown) return null;
      info.textContent = "도서번호를 입력하거나, 목록에서 도서를 선택 후 반납해주세요.";
      ok.textContent = "반납";
      return shown;
    }

    async function giveBack(barcode) {
      const preview = await post("return", { barcode, answers: { ...RETURN_ANSWERS, preview: true } });
      if (preview.error || !preview.preview) {
        await msg(preview.error || "반납할 수 없는 도서입니다.");
        return c.focus();
      }
      const p = preview.preview;
      // CLIB shows the borrower first
      if (p.userId) await selectUser(p.userId);
      if (!await confirmDetails("반납하시겠습니까?", p)) return c.focus();
      const result = await post("return", { barcode, answers: RETURN_ANSWERS });
      if (result.error || !result.ok) {
        await msg(result.error || "반납하지 못했습니다.");
        return c.focus();
      }
      // 연체 notices (대출정지, 연체금)
      await messages(result.messages);
      if (result.userId) await selectUser(result.userId);
      if (!await goOn("반납이 정상적으로 처리되었습니다.", "다른 도서를 계속 반납하시겠습니까?",
        "(예 : 계속반납, 아니오 : 초기화면으로)")) return show("home");
      c.focus();
    }

    // Enter: a member number shows their books; anything else is returned as a book
    async function enter(fromButton) {
      if (busy) return;
      const code = c.input.value.trim().toUpperCase();
      if (!code) return msg("회원번호나 도서번호를 입력해주세요.");
      busy = true;
      try {
        if (fromButton && ok.textContent === "반납") await giveBack(code);
        else if (!await selectUser(code)) await giveBack(code);
      } catch (e) {
        await msg(e.message);
      } finally {
        busy = false;
      }
    }
    c.input.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) enter(false); });
    ok.addEventListener("click", () => enter(true));
  })();

  // ---- 도서검색 (SearchBook) -----------------------------------------------------------

  (function () {
    const root = $("#search");
    const field = $("#search-field");
    const text = $("#search-text");
    const results = $(".results", root);
    const COLUMNS = [["순번", "no", 80], ["도서상태", "state", 100], ["등록번호", "barcode", 150], ["서명", "title", 420],
      ["저자", "author", 150], ["출판사", "publisher", 150], ["소장위치", "location", 150], ["발행년도", "year", 90],
      ["청구기호", "claim", 150], ["반납예정일", "dueDate", 110]];
    let running = false;

    function reset() {
      text.value = "";
      field.selectedIndex = 0;
      grid(results, COLUMNS, [], { sortable: true });
      setTimeout(() => text.focus());
    }
    screens.search = { reset };

    async function search(all) {
      if (!all && !text.value.trim()) return msg("검색어를 입력해주세요.");
      if (running) return msg("아직 검색이 진행중입니다.");
      running = true;
      document.body.style.cursor = "wait";
      try {
        const rows = await get("search", all ? {} : { field: field.value, q: text.value.trim() });
        grid(results, COLUMNS, rows || [], { sortable: true });
        if (!rows || !rows.length) await msg("검색 결과가 없습니다.");
      } catch (e) {
        await msg(e.message);
      } finally {
        running = false;
        document.body.style.cursor = "";
      }
    }
    text.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) search(false); });
    $("#search-go").addEventListener("click", () => search(false));
    $("#search-all").addEventListener("click", () => search(true));
  })();

  show("home");
})();
