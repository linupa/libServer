// 분류기호 검색 (Category.cs): CLIB's KDC tree (주류 > 강목 > 요목, "code : name").
// Double-click, Enter or 선택 puts the code into 도서관리's 분류기호. The 찾기 box is not in
// CLIB: it narrows the tree to the codes and names that contain what is typed.
(function () {
  window.CLIB_FORMS = window.CLIB_FORMS || {};
  window.CLIB_FORMS.Category = {
    title: "분류기호 검색", w: 380, h: 520, backColor: null, bold: false,
    children: [
      { id: "label_find", type: "label", x: 12, y: 16, w: 36, h: 20, text: "찾기" },
      { id: "txt_find", type: "text", x: 52, y: 12, w: 316, h: 22 },
      { id: "tree", type: "panel", x: 12, y: 42, w: 356, h: 424 },
      { id: "btn_select", type: "button", x: 128, y: 476, w: 116, h: 32, text: "선택", bold: true },
      { id: "btn_close", type: "button", x: 252, y: 476, w: 116, h: 32, text: "닫기", bold: true },
    ],
  };

  window.CLIB_LOGIC = window.CLIB_LOGIC || {};
  window.CLIB_LOGIC.Category = {
    ownClose: true,
    server: true,
    async init(ctx) {
      const $ = ctx.input;
      const box = ctx.box("tree");
      box.classList.add("kdc-tree");
      box.setAttribute("role", "tree");
      box.tabIndex = 0;
      let items = [];     // [{ node, depth, parent, el }] in tree order
      let current = null; // the selected item

      function pick(item = current) {
        if (!item) return ctx.msgBox("분류기호를 선택해주세요.");
        ctx.bus.emit("pickCategory", item.node.code);
        ctx.close();
      }
      function select(item) {
        if (current) current.el.classList.remove("selected");
        current = item;
        if (!item) return;
        item.el.classList.add("selected");
        item.el.scrollIntoView({ block: "nearest" });
      }
      const open = item => item.el.getAttribute("aria-expanded") === "true";
      function expand(item, on) {
        if (!item.node.children || !item.node.children.length) return;
        item.el.setAttribute("aria-expanded", String(on));
        item.el.querySelector(".kdc-toggle").textContent = on ? "▾" : "▸";
        show();
      }
      // An item shows when every parent is expanded (and, while searching, when it matches)
      function show() {
        for (const item of items) {
          let p = item.parent;
          while (p && open(p)) p = p.parent;
          item.el.hidden = !!p || item.filtered;
        }
      }

      function build(tree) {
        box.replaceChildren();
        items = [];
        const add = (node, depth, parent) => {
          const leaf = !node.children || !node.children.length;
          const el = document.createElement("div");
          el.className = "kdc-node";
          el.setAttribute("role", "treeitem");
          if (!leaf) el.setAttribute("aria-expanded", "false");
          el.style.paddingLeft = `${4 + depth * 18}px`;
          const toggle = Object.assign(document.createElement("span"), { className: "kdc-toggle", textContent: leaf ? "" : "▸" });
          el.append(toggle, `${node.code} : ${node.name}`);
          const item = { node, depth, parent, el, filtered: false };
          items.push(item);
          box.append(el);
          toggle.addEventListener("click", e => { e.stopPropagation(); select(item); expand(item, !open(item)); });
          el.addEventListener("click", () => select(item));
          el.addEventListener("dblclick", () => (leaf ? pick(item) : expand(item, !open(item))));
          (node.children || []).forEach(c => add(c, depth + 1, item));
        };
        tree.forEach(n => add(n, 0, null));
        show();
      }

      // 찾기: matching items, what is under them, and their parents show, opened up to them
      function filter() {
        const word = $("txt_find").value.trim().toLowerCase();
        for (const item of items) item.filtered = !!word;
        items.forEach((item, i) => {
          if (!word || !`${item.node.code} ${item.node.name}`.toLowerCase().includes(word)) return;
          item.filtered = false;
          for (let j = i + 1; j < items.length && items[j].depth > item.depth; j++) items[j].filtered = false;
          for (let p = item.parent; p; p = p.parent) {
            p.filtered = false;
            if (!open(p)) expand(p, true);
          }
        });
        if (!word) items.forEach(item => { if (item.parent && open(item)) expand(item, false); });
        show();
        if (current && current.el.hidden) select(null);
      }

      // Arrow keys move through the shown items; right / left open and close, Enter picks
      box.addEventListener("keydown", e => {
        const shown = items.filter(i => !i.el.hidden);
        const at = shown.indexOf(current);
        if (e.key === "ArrowDown") select(shown[Math.min(at + 1, shown.length - 1)] || shown[0]);
        else if (e.key === "ArrowUp") select(shown[Math.max(at - 1, 0)] || shown[0]);
        else if (e.key === "ArrowRight" && current) expand(current, true);
        else if (e.key === "ArrowLeft" && current) (open(current) ? expand(current, false) : current.parent && select(current.parent));
        else if (e.key === "Enter") pick();
        else return;
        e.preventDefault();
      });
      $("txt_find").addEventListener("input", filter);
      // ↓ or Enter goes from 찾기 to the first item shown (Enter picks the selected one)
      $("txt_find").addEventListener("keydown", e => {
        if (e.isComposing || (e.key !== "ArrowDown" && e.key !== "Enter")) return;
        e.preventDefault();
        if (e.key === "Enter" && current && !current.el.hidden) return pick();
        box.focus();
        select(items.find(i => !i.el.hidden));
      });
      $("btn_select").addEventListener("click", () => pick());
      $("btn_close").addEventListener("click", () => ctx.close());

      box.textContent = "불러오는 중…";
      try {
        const tree = await ctx.library.categories();
        if (!tree.length) box.textContent = "분류기호 자료가 없습니다.";
        else build(tree);
      } catch (e) {
        box.textContent = `분류기호를 불러오지 못했습니다. ${e.message}`;
      }
      setTimeout(() => $("txt_find").focus());
    },
  };
})();
