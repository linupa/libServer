(function () {
  const UI = window.CLIB_UI;
  const MENUS = window.CLIB_MENUS;
  const icon = window.CLIB_ICON;
  const data = window.CLIB.data;
  const $ = (sel, el = document) => el.querySelector(sel);
  const screens = Object.fromEntries(UI.screens.map(s => [s.id, s]));
  // Ported forms without tables (회원증 출력, …) are screens too
  for (const [id, f] of Object.entries(window.CLIB_FORMS || {})) {
    if (!screens[id]) screens[id] = { id, title: f.title || id, size: [f.w, f.h], tables: [] };
  }

  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v;
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return el;
  }

  const LOCK_ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1.5"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2"/></svg>';
  const UNLOCK_ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1.5"/><path d="M5.5 7V5a2.5 2.5 0 0 1 4.9-.7"/></svg>';
  // String-valued columns that still read as amounts; codes like 분류기호 stay left-aligned
  const NUMERIC_KEYS = new Set(["overdueFee", "unpaidFee", "totalFee", "price", "ratio"]);

  function screenTitle(id) {
    return (MENUS.composites[id] || screens[id] || {}).title || id;
  }

  // ---- ported screens ------------------------------------------------------

  // A screen is usable once its form and its logic are ported; the others are disabled
  const NOT_PORTED = "아직 웹으로 옮기지 않은 기능입니다.";
  const ported = id => !!(window.CLIB_FORMS && window.CLIB_FORMS[id] && window.CLIB_LOGIC && window.CLIB_LOGIC[id]);
  const ready = item => (item.children ? item.children.some(ready)
    : !!(item.view || item.dialog) && (!item.view || ported(item.view)) && (!item.dialog || ported(item.dialog)));

  // ---- routing: #/<tab>/<view or ->/<dialog>/<dialog>... ----------------

  function parseHash() {
    const [tab, view, ...dialogs] = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    return {
      tab: MENUS.tabs.some(t => t.id === tab && t.items.some(ready)) ? tab : MENUS.tabs[0].id,
      view: view && view !== "-" && ported(view) ? view : null,
      dialogs: dialogs.filter(ported),
    };
  }

  function go(state) {
    const parts = [state.tab, state.view || "-", ...state.dialogs];
    const hash = `#/${parts.join("/")}`.replace(/\/-$/, "");
    if (location.hash !== hash) location.hash = hash;
    else render();
  }

  let current = parseHash();

  function render() {
    const prev = current;
    current = parseHash();
    renderTabs();
    renderToolbar();
    if (prev.view !== current.view || !$("#workspace").childElementCount) renderWorkspace();
    renderDialogs();
    const top = current.dialogs[current.dialogs.length - 1];
    document.title = `CLIB Web${current.view || top ? " - " + screenTitle(top || current.view) : ""}`;
    showDataSource(top || current.view);
  }

  // ---- tab strip and toolbar ----------------------------------------------

  function renderTabs() {
    $("#tabs").replaceChildren(...MENUS.tabs.map(t => h("button", {
      type: "button", role: "tab", class: "tab",
      "aria-selected": String(t.id === current.tab),
      disabled: t.items.some(ready) ? null : "", title: t.items.some(ready) ? null : NOT_PORTED,
      onclick: () => go({ tab: t.id, view: firstView(t) || current.view, dialogs: [] }),
    }, t.label)));
  }

  // The first page a tab's toolbar opens (도서관리 → 도서관리); a tab of dialogs only keeps the view
  function firstView(tab) {
    const items = tab.items.flatMap(i => i.children || [i]);
    const item = items.find(i => i.view && ready(i));
    return item ? item.view : null;
  }

  function activate(item) {
    if (!ready(item)) return;
    go({
      tab: current.tab,
      view: item.view || current.view,
      dialogs: item.dialog ? [item.dialog] : [],
    });
  }

  function closeMenus() {
    document.querySelectorAll(".tool.open").forEach(el => {
      el.classList.remove("open");
      $("button", el).setAttribute("aria-expanded", "false");
    });
  }

  function renderToolbar() {
    const tab = MENUS.tabs.find(t => t.id === current.tab);
    const bar = $("#toolbar");
    bar.setAttribute("aria-label", `${tab.label} 도구`);
    const items = [];
    tab.items.forEach((item, i) => {
      if (i) items.push(h("span", { class: "sep", "aria-hidden": "true" }));
      const active = item.view && item.view === current.view && !item.dialog;
      const btn = h("button", {
        type: "button", class: `tool-btn${active ? " active" : ""}`,
        disabled: ready(item) ? null : "", title: ready(item) ? null : NOT_PORTED,
        "aria-haspopup": item.children ? "menu" : null,
        "aria-expanded": item.children ? "false" : null,
        html: icon(item.icon),
        onclick: e => {
          if (!item.children) return activate(item);
          e.stopPropagation();
          const wrap = e.currentTarget.parentElement;
          const open = !wrap.classList.contains("open");
          closeMenus();
          wrap.classList.toggle("open", open);
          e.currentTarget.setAttribute("aria-expanded", String(open));
          if (open) {
            const r = e.currentTarget.getBoundingClientRect();
            const menu = $(".dropdown", wrap);
            menu.style.left = `${Math.min(r.left, innerWidth - menu.offsetWidth - 4)}px`;
            menu.style.top = `${r.bottom}px`;
            $("button:not(:disabled)", menu).focus();
          }
        },
      }, h("span", { class: "tool-label" }, item.label, item.children ? h("span", { class: "caret" }, "▾") : null));
      items.push(h("div", { class: "tool" }, btn, item.children
        ? h("div", { class: "dropdown", role: "menu" }, item.children.map(c => h("button", {
            type: "button", role: "menuitem",
            disabled: ready(c) ? null : "", title: ready(c) ? null : NOT_PORTED,
            onclick: () => { closeMenus(); activate(c); },
          }, c.label)))
        : null));
    });
    bar.replaceChildren(...items);
  }

  // ---- workspace ----------------------------------------------------------

  function renderWorkspace() {
    const ws = $("#workspace");
    if (!current.view) {
      ws.replaceChildren(h("div", { class: "splash" },
        h("div", { class: "logo", "aria-hidden": "true" }, h("span", { class: "ring" }, "C"), h("span", {}, "LIB", h("small", {}, "web"))),
        h("p", {}, "작은도서관 관리 프로그램 · 웹 이식판"),
        h("p", { class: "muted" }, "위의 메뉴에서 작업을 선택하세요.")));
      return;
    }
    const view = h("section", { class: "view", "aria-label": screenTitle(current.view) });
    ws.replaceChildren(view);
    buildScreen(view, current.view);
  }

  // ---- dialogs ------------------------------------------------------------

  let zTop = 10;

  function renderDialogs() {
    const layer = $("#dialogs");
    // Message boxes share the layer; a dialog that closes and then shows one (선택된 도서가
    // 없습니다) re-renders here after the box is already up, so leave them alone
    const windows = () => [...layer.children].filter(d => d.dataset.id);
    const open = windows().map(d => d.dataset.id);
    // Keep dialogs that are still open so their position and filters survive
    windows().forEach((d, i) => { if (current.dialogs[i] !== d.dataset.id) d.remove(); });
    current.dialogs.forEach((id, i) => {
      if (open[i] === id && windows()[i]) return;
      layer.append(makeDialog(id, i));
    });
    layer.classList.toggle("active", layer.children.length > 0);
    const top = windows().pop();
    if (top && !$(".msgbox", layer) && !top.contains(document.activeElement)) $(".close", top).focus();
  }

  function closeTopDialog() {
    go({ ...current, dialogs: current.dialogs.slice(0, -1) });
  }

  function makeDialog(id, depth) {
    const screen = screens[id];
    const [w, hgt] = (screen && screen.size) || [640, 420];
    // Ported forms open at exactly their CLIB size; table-only previews get a usable minimum
    const exact = window.CLIB_FORMS && window.CLIB_FORMS[id] && window.CLIB_LOGIC && window.CLIB_LOGIC[id];
    const titleId = `dlg-${id}`;
    const win = h("div", {
      class: "window", role: "dialog", "aria-modal": "true", "aria-labelledby": titleId, "data-id": id,
      style: `width:${(exact ? w : Math.max(w, 480)) + 2}px;height:${(exact ? hgt : Math.max(hgt, 320)) + 33}px;z-index:${++zTop}`,
    });
    const titlebar = h("div", { class: "titlebar" },
      h("span", { id: titleId }, screenTitle(id)),
      h("button", { type: "button", class: "close", "aria-label": "닫기", onclick: closeTopDialog }, "✕"));
    const body = h("div", { class: "window-body" });
    win.append(titlebar, body);
    buildScreen(body, id);
    const logic = window.CLIB_LOGIC && window.CLIB_LOGIC[id];
    if (!(logic && logic.ownClose && window.CLIB_FORMS[id])) {
      body.append(h("div", { class: "window-foot" },
        h("button", { type: "button", class: "btn", onclick: closeTopDialog }, "닫기")));
    }

    // Grow to fit the form when its controls reach past the designer size (CLIB draws
    // these dialogs slightly larger than their ClientSize), then center over the workspace,
    // cascading nested dialogs
    requestAnimationFrame(() => {
      const form = $(".form", win);
      if (form) {
        const dw = form.scrollWidth - form.clientWidth;
        const dh = form.scrollHeight - form.clientHeight;
        if (dw > 0) win.style.width = `${Math.min(innerWidth - 8, win.offsetWidth + dw + 4)}px`;
        if (dh > 0) win.style.height = `${Math.min(innerHeight - 8, win.offsetHeight + dh + 4)}px`;
      }
      const ws = $("#workspace").getBoundingClientRect();
      const left = Math.max(4, ws.left + (ws.width - win.offsetWidth) / 2 + depth * 24);
      const top = Math.max(4, ws.top + Math.max(0, (ws.height - win.offsetHeight) / 2) + depth * 24);
      win.style.left = `${left}px`;
      win.style.top = `${top}px`;
    });
    dragBy(titlebar, win);
    return win;
  }

  function dragBy(handle, win) {
    handle.addEventListener("pointerdown", e => {
      if (e.target.closest("button") || e.button !== 0) return;
      const sx = e.clientX - win.offsetLeft, sy = e.clientY - win.offsetTop;
      handle.setPointerCapture(e.pointerId);
      const move = ev => {
        win.style.left = `${Math.min(Math.max(ev.clientX - sx, -win.offsetWidth + 80), innerWidth - 80)}px`;
        win.style.top = `${Math.min(Math.max(ev.clientY - sy, 0), innerHeight - 30)}px`;
      };
      const up = () => { handle.removeEventListener("pointermove", move); handle.removeEventListener("pointerup", up); };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", up);
    });
  }

  // MessageBox.Show(). Resolves with the index of the button pressed (-1 for close/Esc).
  function msgBox(text, { title = "CLIB", buttons = ["확인"], kind = "info" } = {}) {
    return new Promise(resolve => {
      const layer = $("#dialogs");
      const prevFocus = document.activeElement;
      const btns = buttons.map((label, i) => h("button", { type: "button", class: "btn", onclick: () => close(i) }, label));
      const box = h("div", { class: "window msgbox", role: "alertdialog", "aria-modal": "true", "aria-label": title, style: `z-index:${++zTop}` },
        h("div", { class: "titlebar" }, h("span", {}, title),
          h("button", { type: "button", class: "close", "aria-label": "닫기", onclick: () => close(-1) }, "✕")),
        h("div", { class: "msg-body" },
          h("span", { class: `msg-icon ${kind}`, "aria-hidden": "true" }, kind === "question" ? "?" : "i"),
          h("p", {}, text)),
        h("div", { class: "msg-foot" }, btns));
      function close(result) {
        box.remove();
        layer.classList.toggle("active", layer.children.length > 0);
        if (prevFocus && prevFocus.isConnected) prevFocus.focus();
        resolve(result);
      }
      box.addEventListener("keydown", e => { if (e.key === "Escape") { e.stopPropagation(); close(-1); } });
      layer.append(box);
      layer.classList.add("active");
      box.style.left = `${(innerWidth - box.offsetWidth) / 2}px`;
      box.style.top = `${Math.max(40, (innerHeight - box.offsetHeight) / 2 - 40)}px`;
      dragBy($(".titlebar", box), box);
      btns[0].focus();
    });
  }

  function showNotice(id, data) {
    return new Promise(resolve => {
      const form = window.CLIB_FORMS[id];
      const layer = $("#dialogs");
      const win = h("div", { class: "window notice", role: "status", "aria-live": "assertive",
        style: `width:${form.w}px;height:${form.h}px;z-index:${++zTop}` });
      layer.append(win);
      layer.classList.add("active");
      const close = () => {
        win.remove();
        layer.classList.toggle("active", layer.children.length > 0);
        resolve();
      };
      buildForm(win, id, { ...data, close, resize: (w, hgt) => { win.style.width = `${w}px`; win.style.height = `${hgt}px`; } });
      const ws = $("#workspace").getBoundingClientRect();
      win.style.left = `${ws.left + (ws.width - win.offsetWidth) / 2}px`;
      win.style.top = `${ws.top + Math.max(0, (ws.height - win.offsetHeight) / 2)}px`;
    });
  }

  const confirmBox = (text, title) =>
    msgBox(text, { title, buttons: ["예(Y)", "아니요(N)"], kind: "question" }).then(i => i === 0);

  // ---- screens ------------------------------------------------------------

  function openLink(id) {
    if (!ported(id)) return msgBox(NOT_PORTED);
    go({ ...current, dialogs: [...current.dialogs, id] });
  }

  function buildScreen(container, id) {
    if (window.CLIB_FORMS && window.CLIB_FORMS[id] && window.CLIB_LOGIC && window.CLIB_LOGIC[id]) {
      buildForm(container, id);
      return;
    }
    const links = MENUS.links[id] || [];
    const composite = MENUS.composites[id];
    const screen = screens[id];

    const panel = h("div", { class: "screen" });
    container.append(panel);
    if (links.length) {
      panel.append(h("div", { class: "command-row" }, links.map(([target, label]) =>
        h("button", { type: "button", class: "btn", onclick: () => openLink(target) }, label))));
    }

    if (composite) {
      if (!composite.options.length) {
        panel.append(h("div", { class: "placeholder" },
          `${composite.title} 화면에는 표가 없어 아직 옮기지 않았습니다.`));
        return;
      }
      // 이용현황: one result table at a time, picked with radio buttons
      const area = h("div", { class: "tables" });
      const name = `opt-${id}`;
      const show = target => {
        const s = screens[target];
        area.replaceChildren();
        addTables(area, s, s.tables, false);
      };
      panel.append(h("fieldset", { class: "options" },
        h("legend", {}, "조회 구분"),
        composite.options.map(([target, label], i) => h("label", {},
          h("input", { type: "radio", name, checked: i === 0, onchange: () => show(target) }), label))), area);
      show(composite.options[0][0]);
      return;
    }

    const area = h("div", { class: "tables" });
    // Screens with many lists (대출/반납 통계) show one at a time, like CLIB's option buttons
    if (screen.tables.length > 3) {
      const name = `opt-${id}`;
      const show = t => { area.replaceChildren(); addTables(area, screen, [t], true); };
      panel.append(h("fieldset", { class: "options" },
        h("legend", {}, "보기"),
        screen.tables.map((t, i) => h("label", {},
          h("input", { type: "radio", name, checked: i === 0, onchange: () => show(t) }), t.label))), area);
      show(screen.tables[0]);
    } else {
      panel.append(area);
      addTables(area, screen, screen.tables, screen.tables.length > 1);
    }
  }

  function addTables(area, screen, tables, labelled) {
    for (const table of tables) {
      const box = h("section", { class: "grid-box" });
      area.append(box);
      data.getRows(screen, table).then(rows => renderTable(box, screen, table, rows, labelled));
    }
  }

  // ---- forms laid out like the WinForms designer ---------------------------

  // Puts each control at its CLIB Location/Size. The form's logic decides how the
  // top-level controls stretch (CLIB does this in its SizeChanged handler), either
  // with a `layout` split or an `arrange` function; everything inside a panel,
  // group box or tab keeps its designer coordinates.
  function buildForm(container, id, params = {}) {
    const form = window.CLIB_FORMS[id];
    const logic = window.CLIB_LOGIC[id];
    const screen = screens[id];
    const controls = {};
    const lists = {};
    const columns = (logic.layout && logic.layout.columns) || logic.columns || {};
    // Per-list options from the logic: { editable: [keys], rowNumbers: true }
    const listOpts = logic.lists || {};

    const root = h("div", {
      class: `form form-${id}${form.bold ? " bold-form" : ""}`,
      style: form.backColor ? `--form-back:${form.backColor}` : null,
    });
    container.append(root);

    function control(n, groupName) {
      const pos = `left:${n.x}px;top:${n.y}px;width:${n.w}px;height:${n.h}px`;
      const colors = `${n.back ? `background:${n.back};` : ""}${n.fore ? `color:${n.fore};` : ""}`;
      const domId = `${id}-${n.id}`;
      let el;
      switch (n.type) {
        case "label": {
          // AutoSize labels sit at their location; aligned labels fill their box (TextAlign)
          const box = n.align
            ? `${pos};display:flex;align-items:${{ top: "flex-start", middle: "center", bottom: "flex-end" }[n.valign]};` +
              `justify-content:${{ left: "flex-start", center: "center", right: "flex-end" }[n.align]};`
            : `left:${n.x}px;top:${n.y}px;`;
          el = h("label", { class: `ctl label${n.bold ? " bold" : ""}`, style: box + colors }, n.text);
          break;
        }
        case "text":
          el = h(n.multiline ? "textarea" : "input", {
            class: `ctl textbox${n.readOnly ? " ro" : ""}`, id: domId, style: pos + ";" + colors,
            type: n.multiline ? null : "text", readonly: !!n.readOnly, autocomplete: "off", spellcheck: "false",
          });
          if (n.text) el.value = n.text;
          break;
        case "date":
          el = h("input", { class: "ctl textbox", id: domId, type: "date", style: pos });
          break;
        case "combo":
          el = h("select", { class: `ctl combo${n.bold ? " bold" : ""}`, id: domId, style: pos },
            [...new Set([...(n.text && !n.items.includes(n.text) ? [n.text] : []), ...n.items])]
              .map(v => h("option", { value: v }, v)));
          if (n.text) el.value = n.text;
          break;
        case "picture":
          el = h("div", { class: "ctl picture", style: pos }, h("img", { alt: "", hidden: true }));
          break;
        case "progress":
          el = h("progress", { class: "ctl progress", id: domId, style: pos, max: 1, value: 0 });
          break;
        case "radio":
        case "check":
          // Appearance.Button radios look like toggle buttons
          el = h("label", { class: `ctl choice${n.bold ? " bold" : ""}${n.pushLike ? " push" : ""}`, style: pos },
            h("input", { type: n.type === "radio" ? "radio" : "checkbox", id: domId, name: n.type === "radio" ? `${id}-${groupName}` : null, checked: !!n.checked }),
            n.text);
          break;
        case "button":
          el = h("button", { type: "button", class: `ctl btn${n.bold ? " bold" : ""}`, id: domId, style: pos + ";" + colors }, n.text);
          break;
        case "group":
          // A coloured GroupBox fills its whole area, caption row included
          el = h("div", { class: "ctl group", role: "group", "aria-label": n.text, style: pos + (n.back ? `;background:${n.back}` : "") },
            h("span", { class: "group-caption", "aria-hidden": "true", style: n.back ? `background:${n.back}` : null }, n.text));
          break;
        case "tabs":
          el = buildTabs(n);
          break;
        case "list": {
          el = h("div", { class: "ctl list", style: pos });
          const table = screen.tables.find(t => t.id === n.id);
          if (table) lists[n.id] = renderTable(el, screen, table, [], false, { plain: true, fitColumns: columns[n.id], ...listOpts[n.id] });
          break;
        }
        default:
          el = h("div", { class: "ctl panel", style: pos + ";" + colors });
      }
      if (n.hidden) el.hidden = true;
      controls[n.id] = n.type === "radio" || n.type === "check" ? $("input", el) : el;
      controls[`${n.id}:box`] = el;
      if (n.children && n.type !== "tabs") addChildren(el, n);
      return el;
    }

    function addChildren(el, n) {
      // Reading order: rows top to bottom, then left to right
      const row = c => Math.floor((c.y + c.h / 2) / 20);
      const kids = [...n.children].sort((a, b) => row(a) - row(b) || a.x - b.x);
      kids.forEach(c => el.append(control(c, n.id)));
      // Point each label at the input to its right on the same row
      kids.filter(c => c.type === "label").forEach(l => {
        const target = kids.filter(c => ["text", "combo", "date"].includes(c.type) && c.x > l.x &&
          Math.abs((c.y + c.h / 2) - (l.y + l.h / 2)) < 10).sort((a, b) => a.x - b.x)[0];
        if (target) controls[`${l.id}:box`].setAttribute("for", `${id}-${target.id}`);
      });
    }

    // TabControl: a strip of tab buttons over stacked pages
    function buildTabs(n) {
      const el = h("div", { class: "ctl tabs", style: `left:${n.x}px;top:${n.y}px;width:${n.w}px;height:${n.h}px` });
      const strip = h("div", { class: "tab-strip", role: "tablist" });
      el.append(strip);
      // Multi-row tab strips give pages different Y offsets in the designer; ours is one row
      const pageTop = Math.min(...n.children.map(p => p.y));
      const pages = n.children.map((p, i) => {
        const page = h("div", {
          class: "tab-page", role: "tabpanel", id: `${id}-${p.id}`, "aria-labelledby": `${id}-${p.id}-tab`,
          style: `left:${p.x - 2}px;top:${pageTop}px;width:${p.w}px;height:${n.h - pageTop - 4}px`,
        });
        addChildren(page, p);
        controls[p.id] = page;
        page.hidden = i !== 0;
        return page;
      });
      const tabs = n.children.map((p, i) => h("button", {
        type: "button", role: "tab", class: "tab-btn", id: `${id}-${p.id}-tab`,
        "aria-selected": String(i === 0), "aria-controls": `${id}-${p.id}`,
        onclick: () => select(i),
      }, p.text));
      function select(i) {
        tabs.forEach((t, k) => t.setAttribute("aria-selected", String(k === i)));
        pages.forEach((pg, k) => { pg.hidden = k !== i; });
        el.dispatchEvent(new CustomEvent("tabchange", { detail: n.children[i].id }));
      }
      el.select = select;
      strip.append(...tabs);
      el.append(...pages);
      return el;
    }

    const nodes = form.children;
    if (logic.arrange) {
      logic.arrange({ root, nodes, render: n => control(n, "form"), controls });
    } else if (!logic.layout) {
      // Fixed-size dialog: every control stays where the designer put it
      nodes.forEach(n => root.append(control(n, "form")));
    } else {
      const layout = logic.layout || {};
      const left = h("div", { class: "form-left" });
      const right = h("div", { class: "form-right" });
      root.classList.add("split");
      root.append(left, right);
      for (const n of nodes) {
        const el = control(n, "form");
        if (layout.right === n.id) {
          right.style.width = `${n.w}px`;
          el.style.cssText = `left:0;top:0;width:${n.w}px;height:${n.h}px`;
          right.append(el);
        } else {
          // Stretch the panel and its list like BookLent_SizeChanged():
          // list width = panel width - 15, list height = panel height - 40
          el.classList.add("stretch");
          el.style.cssText = `flex:${(layout.ratios || {})[n.id] || 1} 1 0`;
          const ln = (n.children || []).find(c => c.type === "list");
          if (ln) controls[`${ln.id}:box`].style.cssText = `left:${ln.x}px;top:${ln.y}px;right:${15 - ln.x}px;bottom:${40 - ln.y}px`;
          left.append(el);
        }
      }
    }

    return logic.init({
      params,
      el: name => controls[name],
      input: name => controls[name],
      box: name => controls[`${name}:box`],
      list: name => lists[name],
      msgBox: (text, title) => msgBox(text, { title }),
      confirm: confirmBox,
      openDialog: target => (ported(target) ? openLink(target) : msgBox(NOT_PORTED)),
      ported,
      // A button for a feature that is not ported yet: greyed out, with a tooltip
      notPorted: (...names) => names.forEach(n => { controls[n].disabled = true; controls[n].title = NOT_PORTED; }),
      // A button opening another dialog; disabled while that dialog is not ported
      dialogButton: (name, target) => {
        if (!ported(target)) return controls[name] && Object.assign(controls[name], { disabled: true, title: NOT_PORTED });
        controls[name].addEventListener("click", () => openLink(target));
      },
      close: () => closeTopDialog(),
      // Close this dialog and open another in its place (SelectUserCard -> UserCardPrint)
      replaceDialog: target => go({ ...current, dialogs: [...current.dialogs.slice(0, -1), target] }),
      bus: window.CLIB.bus,
      library: libraryFor(id),
      // Render another ported form inside an element (환경설정 tabs, the option dialogs);
      // returns what that form's init returns
      embed: (host, formId) => buildForm(host, formId, {}),
      // A borderless form shown over everything, blocking input until it closes itself
      // (LentMsg after 대출 / 반납 / 예약). Resolves when it has closed.
      notice: (formId, data) => showNotice(formId, data),
      // Render one of another screen's tables (이용현황 shows 대출현황 / 예약현황 / 딸림자료)
      table: (host, screenId, tableId, opts = {}) => {
        const sc = screens[screenId];
        return renderTable(host, sc, sc.tables.find(t => t.id === tableId), [], false, { plain: true, ...opts });
      },
    });
  }

  // ---- table (DataGridView / ListView look) -------------------------------

  // Returns { setRows(rows), select(row) } so form logic can drive the list.
  function renderTable(box, screen, table, rows, labelled, opts = {}) {
    let cols = table.columns.filter(c => !c.hidden);
    const state = { sortKey: null, dir: 1, filter: "", selected: null };
    const checkCol = cols.find(c => c.type === "check" && c.key === "checked");
    const name = table.label || screen.title;

    const count = h("span", { class: "count" });
    if (!opts.plain) {
      box.append(h("div", { class: "grid-head" },
        h("span", { class: "grid-title" }, labelled ? name : null, count),
        h("div", { class: "grid-tools" },
          h("label", {}, "검색 ", h("input", {
            type: "search", class: "textbox", "aria-label": `${name} 검색`,
            oninput: e => { state.filter = e.target.value.trim().toLowerCase(); draw(); },
          })),
          h("button", { type: "button", class: "btn", onclick: () => exportCsv() }, "엑셀저장"))));
    }

    const thead = h("thead");
    const tbody = h("tbody");
    // List_SizeChanged(): 순번 is 50px and every other column is (list width - 50) / n.
    // n is a per-list number from CLIB; true means "the remaining columns fit exactly".
    const colgroup = opts.fitColumns
      ? h("colgroup", {}, cols.map(() => h("col")))
      : null;
    const tableEl = h("table", { class: opts.fitColumns ? "fit" : null }, colgroup, thead, tbody);
    const gridEl = h("div", { class: "grid", tabindex: "0", role: "region", "aria-label": name }, tableEl);
    box.append(gridEl);
    if (opts.fitColumns) {
      // "equal": every column gets the same share (ChageListColumnSize in the statistics form)
      const equal = opts.fitColumns === "equal";
      const n = opts.fitColumns === true ? cols.length - 1 : equal ? cols.length : opts.fitColumns;
      new ResizeObserver(() => {
        const first = equal ? 0 : 50;
        const each = Math.max(40, Math.floor((gridEl.clientWidth - first - 2) / n));
        [...colgroup.children].forEach((col, i) => { col.style.width = `${i === 0 && !equal ? 50 : each}px`; });
        tableEl.style.width = `${first + each * (equal ? cols.length : cols.length - 1)}px`;
      }).observe(gridEl);
    }

    function visibleRows() {
      let out = rows;
      if (state.filter) {
        out = out.filter(r => cols.some(c => c.type === "text" && String(r[c.key]).toLowerCase().includes(state.filter)));
      }
      if (state.sortKey) {
        const k = state.sortKey;
        // "12일" sorts as 12 (연체기간; CLIB's SortCompare strips the 일)
        const bare = v => String(v).replace(/,/g, "").replace(/일$/, "");
        const num = v => (typeof v === "number" ? v : parseFloat(bare(v)));
        out = [...out].sort((a, b) => {
          const x = a[k], y = b[k];
          const nx = num(x), ny = num(y);
          const cmp = !isNaN(nx) && !isNaN(ny) && /^[\d.\s-]+$/.test(`${bare(x)}${bare(y)}`)
            ? nx - ny : String(x).localeCompare(String(y), "ko");
          return cmp * state.dir;
        });
      }
      return out;
    }

    function drawHead() {
      const all = h("input", {
        type: "checkbox", "aria-label": "전체 선택",
        onchange: e => { visibleRows().forEach(r => { r.checked = e.target.checked; }); draw(); },
      });
      thead.replaceChildren(h("tr", {}, opts.rowNumbers ? h("th", { class: "row-head", "aria-label": "번호" }) : null, cols.map(c => {
        if (c === checkCol) return h("th", { class: "c-check" }, all);
        const sortable = c.type === "text";
        const sorted = state.sortKey === c.key;
        return h("th", {
          style: c.width ? `min-width:${Math.max(40, Math.min(c.width, 320))}px` : null,
          "aria-sort": sorted ? (state.dir > 0 ? "ascending" : "descending") : null,
          class: c.type !== "text" ? `c-${c.type}` : null,
        }, sortable
          ? h("button", {
              type: "button", class: "sort",
              onclick: () => {
                state.dir = sorted ? -state.dir : 1;
                state.sortKey = c.key;
                drawHead();
                draw();
              },
            }, c.header || " ", h("span", { class: "arrow", "aria-hidden": "true" }, sorted ? (state.dir > 0 ? "▲" : "▼") : ""))
          : c.header);
      })));
    }

    function cell(c, r) {
      const val = r[c.key];
      switch (c.type) {
        case "check":
          return h("td", { class: "c-check" }, h("input", {
            type: "checkbox", checked: !!val, "aria-label": `${c.header || "선택"} ${r.no ?? ""}`,
            onclick: e => e.stopPropagation(),
            onchange: e => { r[c.key] = e.target.checked; },
          }));
        case "button":
          return h("td", { class: "c-button" }, h("button", {
            type: "button", class: "btn mini",
            onclick: e => {
              e.stopPropagation();
              if (opts.onButton) return opts.onButton(r, c.key);
              msgBox(`'${c.header}' (${r.barcode || r.userId || r.no || ""}) 기능은 백엔드 연결 후 동작합니다.`);
            },
          }, val));
        case "image":
          return h("td", { class: `c-image ${val ? "on" : "off"}`, title: val ? "보안 설정됨" : "보안 해제됨", html: val ? LOCK_ICON : UNLOCK_ICON });
        default: {
          if (opts.editable && opts.editable.includes(c.key)) {
            // DataGridView cell edit: typing changes the row in place
            return h("td", { class: "edit" }, h("input", {
              type: "text", value: val ?? "", "aria-label": c.header,
              onclick: e => e.stopPropagation(),
              oninput: e => { r[c.key] = e.target.value; if (opts.onEdit) opts.onEdit(r, c.key); },
            }));
          }
          const numeric = typeof val === "number" || NUMERIC_KEYS.has(c.key);
          return h("td", { class: numeric ? "num" : null }, val);
        }
      }
    }

    function draw() {
      const list = visibleRows();
      // A 순번 column that follows the shown order (CLIB renumbers it after sorting)
      if (opts.renumber) list.forEach((r, i) => { r.no = i + 1; });
      tbody.replaceChildren(...list.map(r => h("tr", {
        class: [state.selected === r ? "selected" : "", opts.rowClass ? opts.rowClass(r) : ""].join(" ").trim() || null,
        onclick: () => {
          state.selected = opts.onRowClick || state.selected !== r ? r : null;
          draw();
          if (opts.onRowClick) opts.onRowClick(r);
        },
      }, opts.rowNumbers ? h("th", { class: "row-head", scope: "row" }, list.indexOf(r) + 1) : null, cols.map(c => cell(c, r)))));
      if (!list.length && !opts.plain) {
        tbody.append(h("tr", {}, h("td", { class: "empty", colspan: cols.length }, "결과가 없습니다.")));
      }
      count.textContent = state.filter ? `${list.length} / ${rows.length}건` : `${rows.length}건`;
    }

    function exportCsv() {
      const textCols = cols.filter(c => c.type === "text");
      const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
      const lines = [textCols.map(c => esc(c.header)).join(","),
        ...visibleRows().map(r => textCols.map(c => esc(r[c.key])).join(","))];
      // BOM so Excel opens Korean text correctly
      const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
      const a = h("a", { href: URL.createObjectURL(blob), download: `${screen.title}_${table.label || table.id}.csv` });
      document.body.append(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
    }

    drawHead();
    draw();
    return {
      setRows(next) { rows = next; state.selected = null; draw(); },
      rows: () => rows,
      select(row) { state.selected = row; draw(); },
      selected: () => state.selected,
      refresh: draw,
      onRowClick(fn) { opts.onRowClick = fn; },
      rowClass(fn) { opts.rowClass = fn; draw(); },
      // A button column's click (번호변경, 삭제, …): fn(row, columnKey)
      onButton(fn) { opts.onButton = fn; },
      hideColumns(keys) {
        cols = table.columns.filter(c => !c.hidden && !keys.includes(c.key));
        if (colgroup) colgroup.replaceChildren(...cols.map(() => h("col")));
        drawHead();
        draw();
      },
      exportCsv: () => exportCsv(),
    };
  }

  // ---- global handlers ----------------------------------------------------

  document.addEventListener("click", closeMenus);
  document.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    if (document.querySelector(".tool.open")) closeMenus();
    else if (current.dialogs.length) closeTopDialog();
  });
  $("#help").addEventListener("click", () =>
    msgBox(`CLIB Web — CLIB의 화면 ${UI.screens.length}개, 표 ${UI.screens.reduce((n, s) => n + s.tables.length, 0)}개를 웹으로 옮기는 중입니다. 데이터는 아직 샘플입니다.`, { title: "도움말" }));
  // Screens move to the database one at a time: those whose logic says `server: true`
  // use the server's library when the page is served by server/app.py
  function libraryFor(id) {
    const logic = window.CLIB_LOGIC && window.CLIB_LOGIC[id];
    return logic && logic.server && window.CLIB.server ? window.CLIB.server : window.CLIB.library;
  }

  function showDataSource(id) {
    const server = window.CLIB.server;
    const el = $("#status-data");
    if (!server) {
      el.textContent = "샘플 데이터 · 서버 미연결";
    } else if (id && libraryFor(id) === server) {
      el.textContent = `CLIB DB 연결됨${server.readOnly ? " (읽기 전용)" : ""} · ${server.database}`;
    } else {
      el.textContent = id ? "이 화면은 아직 샘플 데이터입니다 · 서버 연결됨" : `서버 연결됨 · ${server.database}`;
    }
  }

  // Server or network failures inside screen logic surface as a message box
  window.addEventListener("unhandledrejection", e => {
    msgBox(`서버와 통신하지 못했습니다.\n${e.reason && e.reason.message ? e.reason.message : e.reason}`, { title: "오류" });
  });

  window.addEventListener("hashchange", render);
  (window.CLIB.ready || Promise.resolve()).then(render);
})();
