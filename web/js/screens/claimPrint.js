// 청구기호 출력 (ClaimPrint.cs): spine labels for the books checked in 도서관리's list.
// The options are CLIB.exe.Config CLAIM_*; on the server they go to clib_settings.json instead.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};

window.CLIB_LOGIC.ClaimPrint = {
  ownClose: true,
  server: true,
  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const s = lib.settings.claim;

    $(s.label ? "radio_Label2" : "radio_Label1").checked = true;
    $(s.outline ? "radio_outline1" : "radio_outline2").checked = true;
    $(s.align === "center" ? "radio_aligncenter" : "radio_alignleft").checked = true;
    $("check_barcode").checked = s.barcode;
    $("txt_leftmargin").value = s.leftMargin;
    $("txt_topmargin").value = s.topMargin;
    $("txt_print_location").value = s.skip;
    $("combo_font").selectedIndex = s.font;
    $("txt_FontSize").value = s.fontSize;
    $("chk_v").checked = s.v;
    $("chk_c").checked = s.c;
    $("chk_vUpper").checked = s.vUpper;
    $("chk_cUpper").checked = s.cUpper;

    // KeyPress handlers: the margins and the skip count take digits only
    ["txt_leftmargin", "txt_topmargin", "txt_print_location"].forEach(n =>
      $(n).addEventListener("input", () => { $(n).value = $(n).value.replace(/\D/g, ""); }));

    // chk_v / chk_c show their 대문자로 출력 box and are saved straight away, like CLIB
    async function keep(changes) {
      const saved = await lib.saveSettings({ claim: changes });
      if (saved && saved.error) return ctx.msgBox(saved.error);
      Object.assign(s, changes);
    }
    const syncUpper = () => {
      ctx.box("chk_vUpper").hidden = !$("chk_v").checked;
      ctx.box("chk_cUpper").hidden = !$("chk_c").checked;
    };
    [["chk_v", "v"], ["chk_c", "c"], ["chk_vUpper", "vUpper"], ["chk_cUpper", "cUpper"]].forEach(([n, key]) =>
      $(n).addEventListener("change", () => { syncUpper(); keep({ [key]: $(n).checked }); }));
    syncUpper();

    const esc = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

    // CheckClaim(): six lines per book, a blank line for an empty value
    function lines(b, o) {
      const mark = (value, on, upper, prefix) => (!value ? " " : !on ? value : `${upper ? prefix.toUpperCase() : prefix}.${value}`);
      return [b.exCate || " ", b.category || " ", b.authorCode || " ",
        mark(b.claimVolume, o.v, o.vUpper, "v"), mark(b.copy, o.c, o.cUpper, "c"), b.barcode || " "];
    }

    async function print() {
      if (!$("txt_print_location").value.trim()) $("txt_print_location").value = "0";
      const skip = Number($("txt_print_location").value);
      if (skip > 29) return ctx.msgBox("제외장수는 0 ~ 29 사이만 입력할 수 있습니다.");
      if (!/^\d+$/.test($("txt_FontSize").value.trim())) return ctx.msgBox("폰트크기는 숫자만 입력할 수 있습니다.");
      // CLIB saves the options (not the skip count) before looking at the books
      const options = {
        label: $("radio_Label2").checked ? 1 : 0, outline: $("radio_outline1").checked,
        align: $("radio_aligncenter").checked ? "center" : "left", barcode: $("check_barcode").checked,
        leftMargin: Number($("txt_leftmargin").value) || 0, topMargin: Number($("txt_topmargin").value) || 0,
        font: $("combo_font").selectedIndex, fontSize: Number($("txt_FontSize").value),
      };
      const saved = await lib.saveSettings({ claim: options });
      if (saved && saved.error) return ctx.msgBox(saved.error);
      Object.assign(s, options);

      const out = {};
      ctx.bus.emit("collectBooks", out);
      if (!out.books || !out.books.length) return ctx.msgBox("선택된 도서가 없습니다.");
      const o = { ...s, v: $("chk_v").checked, c: $("chk_c").checked,
        vUpper: $("chk_vUpper").checked, cUpper: $("chk_cUpper").checked };
      // The window stays open for the next batch, as in CLIB
      printLabels(out.books.map(b => lines(b, o)), o, skip);
    }

    // printDocument1_PrintPage(), in millimetres from the paper's corner: five labels across
    // and six down per sheet, the first sheet starting after `skip` labels. CLIB leaves 8 mm
    // between columns; here they touch, so neighbours share one cut line.
    function printLabels(labels, o, skip) {
      const size = o.fontSize;
      // MeasureString("폰트크기") at one point smaller: GDI+ gives about 1.15 em per line
      const H = (size - 1) * 25.4 / 72 * 1.15;
      const W = 30, LABEL = o.label ? { h: 31, gap: 11 } : { h: 26, gap: 16 };
      const lineH = Math.trunc(H + 1);
      const indent = o.align === "center" ? 0 : 5;
      const first = o.label && !o.barcode ? 2 : 1;
      let step;
      if (o.barcode) {
        const need = H * 5 + (o.label ? 10 : 5) + H;
        step = need > LABEL.h ? Math.trunc(LABEL.h / 6) : Math.trunc(H) + (o.label ? 2 : 1);
      } else {
        const need = H * 5 + (o.label ? 12 : 8);
        step = need > LABEL.h ? Math.trunc(LABEL.h / 5) : Math.trunc(H) + (o.label ? 3 : 2);
      }
      const at = (x, y, w, text, small) =>
        `<div class="t${small ? " s" : ""}" style="left:${x}mm;top:${y}mm;width:${w}mm;height:${lineH}mm;line-height:${lineH}mm">${esc(text)}</div>`;

      const pages = [];
      const boxes = [];
      labels.forEach((l, i) => {
        const n = skip + i;
        const slot = n % 30;
        const page = (pages[Math.floor(n / 30)] = pages[Math.floor(n / 30)] || []);
        const x = o.leftMargin + (slot % 5) * W;
        const top = o.topMargin + Math.floor(slot / 5) * (LABEL.h + LABEL.gap);
        // Outlines go into one SVG per sheet: neighbours' shared edge lands on the same
        // coordinates, so it prints as a single cut line
        if (o.outline) (boxes[Math.floor(n / 30)] = boxes[Math.floor(n / 30)] || []).push(
          `<rect x="${x}" y="${top}" width="${W}" height="${LABEL.h}"/>`);
        let y = first + top;
        for (let k = 0; k < 5; k++, y += step) page.push(at(x + indent, y, W - indent, l[k]));
        // 등록번호 포함: as a sixth line; otherwise it goes just under the label
        page.push(at(x + indent, o.barcode ? y : top + LABEL.h + 2, W - indent + 1, l[5], true));
      });

      const family = o.font ? 'Gulim,"굴림",sans-serif' : 'Dotum,"돋움","Malgun Gothic",sans-serif';
      const w = window.open("", "_blank");
      if (!w) return ctx.msgBox("팝업이 차단되어 출력할 수 없습니다.");
      w.document.write(`<!doctype html><meta charset="utf-8"><title>청구기호 출력</title>
        <style>@page{size:A4 portrait;margin:0}*{box-sizing:border-box}body{margin:0;font-family:${family};font-weight:bold;color:#000}
        .page{position:relative;width:210mm;height:297mm;overflow:hidden;break-after:page}
        .box{position:absolute;left:0;top:0;width:210mm;height:297mm}
        .t{position:absolute;text-align:${o.align === "center" ? "center" : "left"};
          overflow:hidden;white-space:nowrap;text-overflow:ellipsis;font-size:${size}pt}
        .t.s{font-size:${size - 1}pt}</style>
        ${pages.map((p, k) => (!p ? "" : `<div class="page">${boxes[k] ? `<svg class="box" viewBox="0 0 210 297"
          fill="none" stroke="#000" stroke-width="0.2">${boxes[k].join("")}</svg>` : ""}${p.join("")}</div>`)).join("")}`);
      w.document.close();
      w.focus();
      w.print();
    }

    $("btn_print").addEventListener("click", print);
    $("btn_cancle").addEventListener("click", () => ctx.close());
  },
};
