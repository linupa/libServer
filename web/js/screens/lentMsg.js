// LentMsg.cs: the borderless notice after 대출 (mode 0), 반납 (1) and 예약 (2).
// It blocks input like ShowDialog() and closes itself after timer1's 500 ms.
window.CLIB_LOGIC = window.CLIB_LOGIC || {};
window.CLIB_LOGIC.LentMsg = {
  init(ctx) {
    const p = ctx.params;
    const box = name => ctx.box(name);
    const add = (name, text) => { box(name).textContent += text ?? ""; };
    const MESSAGES = ["대출되었습니다.", "반납되었습니다.", "예약되었습니다."];
    box("label_msg").textContent = MESSAGES[p.mode] || "";
    add("label_user", p.userName);
    add("label_usercode", p.userId);
    add("label_bookcode", p.barcode);
    if (p.mode === 0) {
      add("label_lent", p.lentDate);
      add("label_return", p.dueDate);
    } else {
      // Returns and reservations: no dates, a shorter window and their own colour
      box("label_lent").hidden = true;
      box("label_return").hidden = true;
      p.resize(306, 138);
      box("panel1").style.height = "118px";
      box("panel1").closest(".form").style.setProperty("--form-back", p.mode === 1 ? "rgb(224, 224, 224)" : "rgb(192, 192, 0)");
    }
    setTimeout(p.close, 500);
  },
};
