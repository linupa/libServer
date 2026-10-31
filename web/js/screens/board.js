// 게시판: the notices in the cloud's `notice` collection (/api/notices), not CLIB's own
// board, which read BookDream's site. Not a CLIB form, so its layout is written here: the
// list on top, the selected notice below, where it can be changed, or a new one written.
(function () {
  // CLIB's board had 작성자 and 조회수; the notices have neither
  const grid = window.CLIB_UI.screens.find(s => s.id === "BoardFrm").tables.find(t => t.id === "BoardGrid");
  grid.columns.forEach(c => { if (c.key === "writer" || c.key === "views") c.hidden = true; });
  grid.columns.find(c => c.key === "title").header = "제목";

  window.CLIB_FORMS = window.CLIB_FORMS || {};
  window.CLIB_FORMS.BoardFrm = {
    title: "게시판", w: 679, h: 618, backColor: null, bold: false,
    children: [
      { id: "BoardGrid", type: "list", x: 0, y: 0, w: 679, h: 280 },
      { id: "label_title", type: "label", x: 0, y: 0, w: 36, h: 22, text: "제목", bold: true },
      { id: "text_title", type: "text", x: 0, y: 0, w: 400, h: 22 },
      { id: "label_date", type: "label", x: 0, y: 0, w: 44, h: 22, text: "작성일", bold: true },
      { id: "date_write", type: "date", x: 0, y: 0, w: 120, h: 22 },
      { id: "text_content", type: "text", x: 0, y: 0, w: 679, h: 300, multiline: true },
      { id: "label_status", type: "label", x: 0, y: 0, w: 400, h: 20, text: "" },
      { id: "btn_delete", type: "button", x: 0, y: 0, w: 100, h: 28, text: "삭제", bold: true },
      { id: "btn_new", type: "button", x: 0, y: 0, w: 100, h: 28, text: "새 글", bold: true },
      { id: "btn_save", type: "button", x: 0, y: 0, w: 100, h: 28, text: "저장", bold: true },
    ],
  };

  // The list takes the top 40% and the notice the rest. Inputs and textareas don't stretch
  // between left and right like a div, so they get their width and height outright.
  const TOP = "40%";
  const PLACES = {
    BoardGrid: `left:6px;right:6px;top:6px;height:calc(${TOP} - 6px)`,
    label_title: `left:6px;top:calc(${TOP} + 10px)`,
    text_title: `left:46px;top:calc(${TOP} + 6px);width:calc(100% - 46px - 190px);height:22px`,
    label_date: `right:132px;top:calc(${TOP} + 10px)`,
    date_write: `right:6px;top:calc(${TOP} + 6px);width:120px;height:22px`,
    text_content: `left:6px;top:calc(${TOP} + 34px);width:calc(100% - 12px);height:calc(100% - ${TOP} - 34px - 42px)`,
    label_status: "left:6px;bottom:14px;right:326px",
    btn_delete: "right:218px;bottom:6px;width:100px;height:28px",
    btn_new: "right:112px;bottom:6px;width:100px;height:28px",
    btn_save: "right:6px;bottom:6px;width:100px;height:28px",
  };

  window.CLIB_LOGIC = window.CLIB_LOGIC || {};
  window.CLIB_LOGIC.BoardFrm = {
    server: true,

    arrange({ root, nodes, render, controls }) {
      nodes.forEach(n => root.append(render(n)));
      for (const [id, place] of Object.entries(PLACES)) {
        controls[`${id}:box`].style.cssText = `${place};box-sizing:border-box`;
      }
    },

    init(ctx) {
      const lib = ctx.library;
      const $ = ctx.input;
      const list = ctx.list("BoardGrid");
      const status = ctx.box("label_status");
      const fields = ["text_title", "date_write", "text_content"];
      let rows = [];
      let current = null;  // the notice being shown; null while writing a new one
      let dirty = false;

      const canEdit = lib.isServer && !lib.readOnly;
      fields.forEach(n => {
        $(n).readOnly = !canEdit;
        $(n).addEventListener("input", () => { dirty = true; });
      });
      ["btn_new", "btn_save"].forEach(n => { $(n).disabled = !canEdit; });
      // Only a notice already saved can be deleted
      const syncDelete = () => { $("btn_delete").disabled = !canEdit || !current; };

      function show(row) {
        current = row;
        list.select(row);
        $("text_title").value = row ? row.title : "";
        $("date_write").value = row ? row.writeDate : lib.today();
        $("text_content").value = row ? row.content : "";
        dirty = false;
        syncDelete();
      }

      const keepChanges = async () => dirty && !await ctx.confirm("수정한 내용이 저장되지 않았습니다.\n저장하지 않고 계속하시겠습니까?", "게시판");

      list.onRowClick(async row => {
        if (row === current) return;
        if (await keepChanges()) return list.select(current);
        show(row);
      });

      $("btn_new").addEventListener("click", async () => {
        if (await keepChanges()) return;
        show(null);
        status.textContent = "새 글을 작성합니다.";
        $("text_title").focus();
      });

      $("btn_save").addEventListener("click", async () => {
        const isNew = !current;
        const body = { title: $("text_title").value, writeDate: $("date_write").value, content: $("text_content").value };
        $("btn_save").disabled = true;
        try {
          const res = await fetch(new URL(`api/notices${isNew ? "" : `/${encodeURIComponent(current.no)}`}`, location.href), {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
          });
          const result = await res.json();
          if (result.error) return ctx.msgBox(result.error);
          dirty = false;
          await load(result.notice.no);
          status.textContent = isNew ? `새 글을 올렸습니다. (글번호 ${result.notice.no})` : "저장했습니다.";
        } catch (e) {
          ctx.msgBox(`저장하지 못했습니다.\n${e.message}`);
        } finally {
          $("btn_save").disabled = !canEdit;
        }
      });

      $("btn_delete").addEventListener("click", async () => {
        if (!current) return;
        const gone = current;
        if (!await ctx.confirm(`"${gone.title}" 공지를 삭제하시겠습니까?\n삭제한 공지는 되돌릴 수 없습니다.`, "게시판")) return;
        $("btn_delete").disabled = true;
        try {
          const res = await fetch(new URL(`api/notices/${encodeURIComponent(gone.no)}/delete`, location.href), { method: "POST" });
          const result = await res.json();
          if (result.error) return ctx.msgBox(result.error);
          dirty = false;
          await load();
          status.textContent = `삭제했습니다. (글번호 ${gone.no})`;
        } catch (e) {
          ctx.msgBox(`삭제하지 못했습니다.\n${e.message}`);
        } finally {
          syncDelete();
        }
      });

      // Load the notices and show the one numbered `no` (or the newest)
      async function load(no) {
        status.textContent = "클라우드에서 공지를 불러오는 중…";
        try {
          const res = await fetch(new URL("api/notices", location.href));
          const body = await res.json();
          if (!res.ok) throw new Error(body && body.error ? body.error : `서버 오류 (${res.status})`);
          rows = body;
          list.setRows(rows);
          show(rows.find(r => r.no === no) || rows[0] || null);
          status.textContent = `공지 ${rows.length}건${lib.readOnly ? " (읽기 전용)" : ""}`;
        } catch (e) {
          status.textContent = e.message;
        }
      }

      syncDelete();
      if (!lib.isServer) {
        status.textContent = "서버에 연결된 경우에만 사용할 수 있습니다.";
        return;
      }
      load();
    },
  };
})();
