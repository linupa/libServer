// 가입신청서 출력 (JoinPrint.cs, Users.printDocument1_PrintPage): CLIB's 회원가입 신청서 and
// 개인정보 동의서 form (Sample\Join.jpg) printed on whole A4 pages, the library's name written
// in 15pt at 75mm and 210mm from the top, as many copies as 출력매수.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.JoinPrint = {
  server: true, // the library's name
  ownClose: true, // ControlBox = false: 출력 / 취소

  init(ctx) {
    const $ = ctx.input;
    $("textBox1").value = "1";
    $("textBox1").style.textAlign = "right";
    // textBox1_KeyPress(): digits only
    $("textBox1").addEventListener("input", e => { e.target.value = e.target.value.replace(/\D/g, ""); });
    $("button2").addEventListener("click", () => ctx.close());
    $("button1").addEventListener("click", () => {
      const copies = parseInt($("textBox1").value, 10);
      if (!(copies > 0)) return ctx.msgBox("출력매수를 입력해주세요.");
      const library = (ctx.library.settings.library.name || "").trim() || "OOOO 도서관";
      const esc = t => t.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
      const image = new URL("img/join.jpg", location.href).href;
      const page = `<section><img src="${image}" alt=""><p style="top:75mm">${esc(library)}</p><p style="top:210mm">${esc(library)}</p></section>`;
      const w = window.open("", "_blank");
      if (!w) return ctx.msgBox("팝업이 차단되어 출력할 수 없습니다.");
      w.document.write(`<!doctype html><meta charset="utf-8"><title>가입신청서 출력</title>
        <style>@page{size:A4;margin:0}body{margin:0}
        section{position:relative;width:210mm;height:297mm;page-break-after:always;overflow:hidden}
        section:last-child{page-break-after:auto}
        img{position:absolute;inset:0;width:100%;height:100%}
        p{position:absolute;left:0;width:210mm;height:20mm;margin:0;text-align:center;
          font:15pt "HY견고딕","HYGothic-Extra","Malgun Gothic",sans-serif}</style>
        ${page.repeat(copies)}`);
      w.document.close();
      // Print once the form image is in
      const img = w.document.images[0];
      const go = () => { w.focus(); w.print(); };
      if (img.complete) go(); else img.addEventListener("load", go, { once: true });
      ctx.close();
    });
  },
};
