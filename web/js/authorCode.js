// 저자기호 (author mark), ported from CLIB's BookManage.CreateAuthorCode() and
// AuthorCode.LJC_Code() / OthersCode(). The options come from 도서관리설정
// (CLIB.exe.Config AUTHORCODE, AUTHOR, BOOK, MOUM); tables from Code/*.csv via authorTables.js.
(function () {
  const CHO = ["ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"];
  const JUNG = ["ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅘ", "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ", "ㅞ", "ㅟ", "ㅠ", "ㅡ", "ㅢ", "ㅣ"];
  // 저자기호 combo order = AUTHORCODE value
  const TABLES = ["동양서저자기호", "이재철1표", "이재철2표", "이재철3표", "이재철4표", "이재철5표",
    "이재철6표", "이재철7표", "이재철8표", "장일세", "Cutter-Sanborn"];
  // Defaults from this install's CLIB.exe.Config
  const DEFAULTS = { table: 5, authorInitial: false, titleInitial: true, moum: true };

  function jamo(ch) {
    const code = (ch || "").charCodeAt(0) - 0xAC00;
    if (!(code >= 0 && code <= 11171)) return null;
    return { cho: CHO[Math.floor(code / 588)], jung: JUNG[Math.floor((code % 588) / 28)] };
  }

  // Drops a leading "(...)", "[...]" or "{...}" and then the brackets themselves
  function stripBrackets(s) {
    for (const [open, close] of [["(", ")"], ["{", "}"], ["[", "]"]]) {
      if (s[0] === open) {
        const end = s.indexOf(close);
        s = end > 0 ? s.slice(end + 1) : s.replace(open, "");
      }
    }
    return s.replace(/[(){}[\]]/g, "");
  }

  // LJC_Code(): which 이재철 file to use depends on the second syllable's consonant
  function ljcFile(n, cho) {
    const pick3 = cho === "ㅊ" ? 3 : cho === "ㄱ" || cho === "ㄷ" ? 2 : 1;
    switch (n) {
      case 1: return "ljc1";
      case 2: return "ljc2";
      case 3: case 4: case 6: return `ljc${n}_${pick3}`;
      case 7: return `ljc7_${cho === "ㅈ" || cho === "ㄲ" ? 3 : cho === "ㄱ" || cho === "ㄷ" ? 2 : 1}`;
      case 8: return `ljc8_${cho === "ㅈ" || cho === "ㄲ" ? 2 : 1}`;
      default: return `ljc5_${cho === "ㅊ" ? 2 : 1}`;
    }
  }

  function ljcCode(author, book, o) {
    const first = jamo(author[0]);
    const second = jamo(author[1]);
    if (!first || !second) return "";
    let text = o.authorInitial ? first.cho : author[0];
    const rows = window.CLIB_AUTHOR_TABLES.ljc[ljcFile(o.table, second.cho)];
    for (let i = 0; i < rows.length; i++) {
      const [key, code] = rows[i];
      if (i < 19) {
        if (key === second.cho) {
          text += code;
          // 자음표2자리 기호보류: a two-digit consonant code stops there
          if (!o.moum && code.length > 1) break;
        }
      } else if (key === second.jung) {
        text += code;
      }
    }
    const initial = jamo(book[0]);
    if (!initial) return "";
    return text + (o.titleInitial ? initial.cho : book[0]);
  }

  // OthersCode(): 동양서 / 장일세 / Cutter-Sanborn look the name up in a sorted table
  function othersCode(author, book, o) {
    const cutter = o.table === 10;
    let text;
    if (cutter) {
      if (!/^[A-Za-z,.' ]+$/.test(author) || !/^[A-Za-z,.' ]+$/.test(book)) return "";
      text = author[0];
    } else {
      const first = jamo(author[0]);
      if (!first) return "";
      text = o.authorInitial ? first.cho : author[0];
    }
    const rows = window.CLIB_AUTHOR_TABLES[cutter ? "cutter" : o.table === 9 ? "jang" : "dongyang"];
    const name = cutter ? author.toLowerCase() : author;
    let code = "";
    for (const [key, value] of rows) {
      if (name < (cutter ? key.toLowerCase() : key)) break;
      code = value;
    }
    text += code;
    if (!o.titleInitial || cutter) return text + book[0];
    const initial = jamo(book[0]);
    return initial ? text + initial.cho : "";
  }

  // Returns { code } or { error } with CLIB's message
  function check(author, title, options) {
    const o = { ...DEFAULTS, ...options };
    const cutter = o.table === 10;
    author = String(author || "");
    if (!cutter) author = author.replace(/[,.']/g, "");
    author = stripBrackets(author.replace(/[ :;/\\!?#$@~\-+=÷&*%]/g, "").trim());
    let book = String(title || "");
    const open = book.indexOf("(");
    if (open >= 0) {
      const close = book.indexOf(")");
      book = close < 0 ? book.replace("(", "") : book.slice(0, open) + book.slice(close + 1);
    }
    book = stripBrackets(book.replace(/[ ,./\\;:!?#$@~\-+=÷&*%'"]/g, "").trim());

    if (!author) return { error: "저자명을 입력해주세요." };
    if (!cutter && author.length < 2) return { error: "저자명은 최소 2글자 이상이어야 합니다.\n괄호, 특수문자 제외" };
    if (!book) return { error: "서명을 입력해주세요." };

    const code = o.table > 0 && o.table < 9 ? ljcCode(author, book, o) : othersCode(author, book, o);
    if (!code) return { error: cutter ? "저자명 또는 서명이 영어가 아닙니다." : "저자명 또는 서명이 한글이 아닙니다." };
    return { code };
  }

  window.CLIB = window.CLIB || {};
  window.CLIB.authorCode = (author, title, options) => check(author, title, options).code || "";
  window.CLIB.authorCode.check = check;
  window.CLIB.authorCode.TABLES = TABLES;
})();
