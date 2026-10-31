// 회원증출력: SelectUserCard.cs asks which kind of card to print, then
// UserCardPrint.cs prints the members checked in 회원관리's list.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};

window.CLIB_LOGIC.SelectUserCard = {
  ownClose: true,
  init(ctx) {
    ctx.input("button1").addEventListener("click", () => ctx.replaceDialog("UserCardPrint"));
    ctx.notPorted("button3");
    ctx.input("button2").addEventListener("click", () => ctx.close());
    setTimeout(() => ctx.input("button1").focus());
  },
};

window.CLIB_LOGIC.UserCardPrint = {
  ownClose: true,
  server: true,
  init(ctx) {
    const lib = ctx.library;
    const $ = ctx.input;
    const s = lib.settings.card;
    const library = lib.settings.library;

    // The card back is three borderless boxes on a white panel
    ["txt_UseInfo", "txt_InfoDetail", "txt_library"].forEach(n => $(n).classList.add("flat"));
    $("txt_UseInfo").value = s.title;
    $("txt_InfoDetail").value = s.notice;
    // The card can carry its own library name (third part of LIBRARY.NOTICE)
    $("txt_library").value = s.libraryName || library.name;
    $("txt_leftmargin").value = s.leftMargin;
    $("txt_topmargin").value = s.topMargin;
    $(s.outline ? "radio_Outline1" : "radio_Outline0").checked = true;

    const esc = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

    async function print() {
      const out = {};
      ctx.bus.emit("collectUsers", out);
      if (!out.total) return ctx.msgBox("회원 목록이 비어있습니다.");
      if (!out.users.length) return ctx.msgBox("선택된 회원이 없습니다.");
      // Keep the edited notice and margins, as CLIB saves them to the LIBRARY table
      // CLIB saves the notice and margins when printing
      const card = {
        title: $("txt_UseInfo").value, notice: $("txt_InfoDetail").value, libraryName: $("txt_library").value,
        leftMargin: Number($("txt_leftmargin").value) || 0, topMargin: Number($("txt_topmargin").value) || 0,
        outline: $("radio_Outline1").checked,
      };
      const saved = await lib.saveSettings({ card });
      if (saved && saved.error) return ctx.msgBox(saved.error);
      Object.assign(s, card);
      const name = card.libraryName;
      const start = [1, 2, 3, 4].find(i => $(`radio_location${i}`).checked) - 1;
      // printDocument1_PrintPage() draws in millimetres: four rows per sheet, 60 mm apart from
      // the top margin, starting at the chosen slot. A row is the front and the back, two
      // 75 x 45 mm boxes side by side; each piece of text sits in its own box at a fixed spot.
      const at = (x, y, w, h, cls, html) =>
        `<div class="${cls}" style="left:${x}mm;top:${y}mm;width:${w}mm;height:${h}mm">${html}</div>`;
      const photo = id => { const url = lib.photoUrl && lib.photoUrl(id); return url ? new URL(url, location.href).href : ""; };
      const pages = [];
      out.users.forEach((u, i) => {
        const n = start + i;
        const page = (pages[Math.floor(n / 4)] = pages[Math.floor(n / 4)] || []);
        const long = u.userId.length > 10;  // longer codes get a wider barcode
        const front = [
          at(0, 3, 75, 5, "c f12", esc(name)),
          at(30, 14, 45, 5, "l f11", `성&nbsp; 명 : ${esc(u.userName)}`),
          at(30, 20, 45, 5, "l f11", `등록일 : ${esc(u.regDate)}`),
          photo(u.userId) ? at(5, 8, 20, 20, "photo", `<img src="${esc(photo(u.userId))}" alt="" onerror="this.remove()">`) : "",
          at(long ? 15 : 17, 29, long ? 45 : 40, 8, "bc", window.CLIB.code128(u.userId)),
          at(0, 38, 75, 5, "c f11", esc(u.userId)),
        ];
        const back = [
          at(0, 3, 75, 7, "c f12", esc(s.title)),
          at(5, 10, 70, 26, "l f8 wrap", esc(s.notice).replace(/\n/g, "<br>")),
          at(0, 38, 75, 5, "c f10", esc(name)),
        ];
        page.push(`<div class="row" style="top:${s.topMargin + (n % 4) * 60}mm;left:${s.leftMargin}mm">
          <div class="card">${front.join("")}</div><div class="card">${back.join("")}</div></div>`);
      });
      const cards = pages.filter(Boolean).map(rows => `<div class="page">${rows.join("")}</div>`);
      const w = window.open("", "_blank");
      if (!w) return ctx.msgBox("팝업이 차단되어 출력할 수 없습니다.");
      w.document.write(`<!doctype html><meta charset="utf-8"><title>회원증 출력</title>
        <style>@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;font-family:Arial,Dotum,"돋움",sans-serif;color:#000}
        .page{position:relative;width:210mm;height:297mm;overflow:hidden;break-after:page}
        .row{position:absolute;display:flex}
        .card{position:relative;width:75mm;height:45mm;${s.outline ? "outline:0.2mm solid #000;outline-offset:-0.1mm;" : ""}}
        .card>div{position:absolute;display:flex;align-items:center;white-space:nowrap}
        .c{justify-content:center}.l{justify-content:flex-start}.wrap{white-space:normal!important;line-height:1.2}
        .f12{font-size:12pt}.f11{font-size:11pt}.f10{font-size:10pt}.f8{font-size:8pt}
        .bc svg{width:100%;height:100%;display:block}
        .photo{justify-content:flex-end;align-items:flex-end!important}.photo img{max-width:20mm;max-height:20mm}</style>
        ${cards.join("")}`);
      w.document.close();
      // Photos have to arrive before the print dialog takes its snapshot
      await Promise.all([...w.document.images].map(img => (img.complete ? null
        : new Promise(done => { img.addEventListener("load", done); img.addEventListener("error", done); }))));
      w.focus();
      w.print();
    }

    $("btn_print").addEventListener("click", print);
    $("btn_cancle").addEventListener("click", () => ctx.close());
  },
};
