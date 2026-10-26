// Data provider for the tables. There is no backend yet, so getRows() returns
// deterministic sample rows built from each column's key. To hook up a server,
// replace getRows() with something like:
//   return fetch(`/api/${screen.id}/${table.id}`).then(r => r.json());
(function () {
  const TITLES = ["어린 왕자", "채식주의자", "소년이 온다", "아몬드", "불편한 편의점", "82년생 김지영",
    "코스모스", "사피엔스", "총, 균, 쇠", "미움받을 용기", "달러구트 꿈 백화점", "토지 1",
    "태백산맥 3", "나미야 잡화점의 기적", "작별하지 않는다", "파친코", "구름빵", "강아지똥",
    "마당을 나온 암탉", "어린이를 위한 한국사", "수학의 정석", "정의란 무엇인가", "데미안",
    "역사의 쓸모", "트렌드 코리아 2026", "해리 포터와 마법사의 돌", "긴긴밤", "흔한남매 15"];
  const AUTHORS = ["김영하", "한강", "손원평", "김호연", "조남주", "칼 세이건", "유발 하라리",
    "재레드 다이아몬드", "기시미 이치로", "이미예", "박경리", "조정래", "히가시노 게이고",
    "이민진", "백희나", "권정생", "황선미", "최태성", "홍성대", "마이클 샌델", "헤르만 헤세"];
  const PUBLISHERS = ["문학동네", "창비", "민음사", "김영사", "사계절", "비룡소", "웅진주니어",
    "다산북스", "위즈덤하우스", "한빛미디어", "나무옆의자", "열린책들"];
  const NAMES = ["김민준", "이서연", "박지호", "최하은", "정도윤", "강서윤", "조예준", "윤지우",
    "장시우", "임수아", "한유진", "오지민", "서하준", "신채원", "권도현", "황민서"];
  const ADDRS = ["서울 마포구 성미산로 12", "경기 안산시 단원구 고잔로 45", "서울 강북구 도봉로 301",
    "경기 수원시 팔달구 효원로 88", "인천 남동구 구월로 7", "서울 노원구 동일로 1402"];
  const POSTS = ["CLIB 업데이트 안내", "RFID 리더기 연결 문의", "휴관일 설정 방법",
    "바코드 출력이 안 됩니다", "데이터 백업 관련 공지", "회원증 출력 양식 변경",
    "국립중앙도서관 ISBN 검색 변경 안내", "엑셀 일괄입력 오류 문의"];
  const MARC_TAGS = [["리더", "000", "N", "Y"], ["ISBN", "020", "Y", "N"],
    ["분류기호(KDC)", "056", "Y", "N"], ["주표목-개인명", "100", "N", "N"],
    ["표제와 책임표시사항", "245", "N", "Y"], ["판사항", "250", "N", "N"],
    ["발행사항", "260", "N", "Y"], ["형태사항", "300", "N", "Y"],
    ["총서사항", "490", "Y", "N"], ["일반주기", "500", "Y", "N"]];

  const pick = (rnd, list) => list[Math.floor(rnd() * list.length)];
  const int = (rnd, lo, hi) => lo + Math.floor(rnd() * (hi - lo + 1));
  const pad = (n, w) => String(n).padStart(w, "0");
  const won = n => n.toLocaleString("ko-KR");

  // Sample dates are spread around 2026-10-19
  const BASE = new Date(2026, 9, 19);
  const day = offset => {
    const d = new Date(BASE);
    d.setDate(d.getDate() + offset);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1, 2)}-${pad(d.getDate(), 2)}`;
  };

  function seeded(str) {
    let h = 2166136261;
    for (const ch of str) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
    return function () {
      h = (h + 0x6D2B79F5) | 0;
      let t = Math.imul(h ^ (h >>> 15), 1 | h);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function makeRow(i, rnd, screen, table) {
    const cols = table.columns;
    const keys = new Set(cols.map(c => c.key));
    const category = `${int(rnd, 0, 9)}${int(rnd, 0, 9)}${int(rnd, 0, 9)}.${int(rnd, 1, 9)}`;
    const author = pick(rnd, AUTHORS);
    const authorCode = `${author[0]}${int(rnd, 11, 99)}${pick(rnd, ["ㄱ", "ㄴ", "ㅅ", "ㅇ", "ㅈ"])}`;
    const lendOffset = -int(rnd, 0, 30);
    const lendDays = 14;
    const overdueDays = Math.max(0, -(lendOffset + lendDays));
    const tag = MARC_TAGS[i % MARC_TAGS.length];
    const userName = pick(rnd, NAMES);

    const v = {
      no: i + 1, seq: 1000 + i, rowKey: 1000 + i, recKey: `KMO${200000000 + int(rnd, 0, 99999999)}`,
      barcode: `EM${pad(10000 + i * 7 + int(rnd, 0, 6), 6)}`,
      uid: `E00401${Array.from({ length: 10 }, () => "0123456789ABCDEF"[int(rnd, 0, 15)]).join("")}`,
      bookState: pick(rnd, ["대출가능", "대출가능", "대출가능", "대출중", "대출중", "예약중", "수리중", "분실"]),
      title: screen.menu === "board" ? pick(rnd, POSTS) : pick(rnd, TITLES),
      author, authorCode, category,
      publisher: pick(rnd, PUBLISHERS),
      volume: rnd() < 0.7 ? "" : String(int(rnd, 1, 5)),
      copy: rnd() < 0.8 ? "" : `c.${int(rnd, 2, 3)}`,
      exCate: pick(rnd, ["", "", "", "아", "참", "J"]),
      isbn: `97911${pad(int(rnd, 0, 99999999), 8)}`,
      location: pick(rnd, ["일반자료실", "어린이자료실", "참고자료실", "보존서고"]),
      bookIn: pick(rnd, ["구입", "구입", "기증", "교환"]),
      regDate: day(-int(rnd, 30, 900)), modDate: day(-int(rnd, 0, 29)),
      marc: "", seriesTitle: rnd() < 0.8 ? "" : pick(rnd, ["창비아동문고", "민음사 세계문학전집", "Why? 시리즈"]),
      userId: `${pick(rnd, ["A", "S", "C"])}${pad(int(rnd, 1, 2400), 5)}`,
      userName, borrower: userName, reserver: pick(rnd, NAMES), writer: pick(rnd, ["관리자", "CLIB", ...NAMES]),
      userGrade: pick(rnd, ["일반", "일반", "학생", "어린이", "교직원"]),
      userState: pick(rnd, ["정상", "정상", "정상", "대출정지", "휴면"]),
      phone: `010-${pad(int(rnd, 0, 9999), 4)}-${pad(int(rnd, 0, 9999), 4)}`,
      address: pick(rnd, ADDRS),
      email: `user${int(rnd, 10, 999)}@example.com`,
      lendDays, maxLend: pick(rnd, [3, 5, 5, 10]), maxReserve: pick(rnd, [1, 2, 3]),
      lendDate: day(lendOffset), dueDate: day(lendOffset + lendDays),
      returnDate: rnd() < 0.5 ? "" : day(lendOffset + int(rnd, 1, 20)),
      overdueDays: overdueDays ? `${overdueDays}일` : "",
      overdueCount: int(rnd, 0, 4),
      overdueFee: won(overdueDays * 100), unpaidFee: won(int(rnd, 0, 5) * 500),
      totalFee: won(overdueDays * 100 + int(rnd, 0, 5) * 500),
      claim: `${category}-${authorCode}`,
      date: day(-int(rnd, 0, 60)),
      memo: pick(rnd, ["대출", "반납"]),
      amount: int(rnd, 0, 3), runningTotal: 10 + i,
      views: int(rnd, 3, 480), writeDate: day(-int(rnd, 0, 400)),
      error: `${pick(rnd, ["245", "260", "300", "056"])} 태그: ${pick(rnd, ["필수 항목 누락", "지시기호 오류", "식별기호 누락"])}`,
      orderInCategory: int(rnd, 1, 60),
      code: pad(i + 1, 3),
      easState: rnd() < 0.7, attach: pick(rnd, ["CD 1매", "부록 1책", "DVD 1매", "지도 1매"]),
      reserveDate: day(-int(rnd, 0, 10)), reserveOrder: int(rnd, 1, 3), reserveExpire: day(int(rnd, 1, 7)),
      count: int(rnd, 3, 900), ratio: (rnd() * 40).toFixed(1),
      state: pick(rnd, ["대출", "반납"]),
      lent: int(rnd, 0, 40), returned: int(rnd, 0, 40), overdue: int(rnd, 0, 5),
      userCount: int(rnd, 5, 80), totalLent: int(rnd, 0, 200), totalOverdue: int(rnd, 0, 12),
      suspendUntil: rnd() < 0.8 ? "" : day(int(rnd, 1, 14)),
      deleteDate: day(-int(rnd, 1, 300)),
      failReason: pick(rnd, ["", "", "회원번호 중복", "회원명 누락", "회원등급 없음"]),
      gradeCode: pad(i + 1, 2), gradeName: ["일반", "학생", "어린이", "교직원", "단체", "기타"][i % 6],
      prefix: "ASCTGE"[i % 6],
      content: `${tag[1]} ${tag[0]}`, year: String(int(rnd, 2008, 2026)),
      bookType: pick(rnd, ["단행본", "단행본", "연속간행물", "비도서"]),
      tagName: tag[0], tag: tag[1], repeatable: tag[2], required: tag[3],
      claimVolume: "", pubPlace: pick(rnd, ["서울", "파주", "고양"]),
      pages: `${int(rnd, 32, 640)} p.`, size: `${pick(rnd, [19, 21, 23, 26])} cm`,
      price: won(int(rnd, 8, 38) * 1000),
      orderNo: i + 1, sum: 0, checked: false, check: false, print: rnd() < 0.5,
    };
    for (let k = 0; k <= 9; k++) v[`kdc${k}`] = int(rnd, 0, 30);
    if (keys.has("sum")) v.sum = Array.from({ length: 10 }, (_, k) => v[`kdc${k}`]).reduce((a, b) => a + b);
    // Settings tables list fixed rows, not random ones
    if (screen.id === "BookOption") Object.assign(v, { location: ["일반자료실", "어린이자료실", "참고자료실", "보존서고"][i] });
    if (screen.id === "LentOption") v.userGrade = v.gradeName;
    // Summary tables have one row per category
    const summary = SUMMARY_ROWS[`${screen.id}/${table.id}`];
    if (summary) Object.assign(v, { [summary.key]: summary.values[i] });

    const row = {};
    for (const c of cols) {
      if (c.type === "button") row[c.key] = c.header;
      else if (c.key in v) row[c.key] = v[c.key];
      else row[c.key] = /^col\d/.test(c.key) ? "" : `${c.header} ${i + 1}`;
    }
    return row;
  }

  const SUMMARY_ROWS = {
    "Lent_ReturnStats/totallist": { key: "state", values: ["대출", "반납"] },
    "BookStats/totallist": { key: "bookState", values: ["대출가능", "대출중", "예약중", "수리중", "분실"] },
    "UserStats/totallist": { key: "userGrade", values: ["일반", "학생", "어린이", "교직원"] },
  };

  function rowCount(screen, table) {
    const summary = SUMMARY_ROWS[`${screen.id}/${table.id}`];
    if (summary) return summary.values.length;
    if (screen.id === "BookOption") return 4;
    if (screen.id === "UserOption" || screen.id === "LentOption") return 5;
    if (table.columns.length <= 3) return 6;
    return 18;
  }

  // ---- sample library for the working screens ---------------------------
  // Member numbers: AA0001- Child, AB0001- Adult, AD0001- Admin, PR0001- Premium.
  // Book barcodes: EM000001-EM000120. Rules and messages follow BookLent.cs,
  // BookReturn.cs, BookReserve.cs and BookManage.cs; codes follow DATA/CODE_SUB.csv.
  // Every rule reads `settings`, which the 환경설정 screens edit.

  const fmt = d => `${d.getFullYear()}-${pad(d.getMonth() + 1, 2)}-${pad(d.getDate(), 2)}`;
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  // "yyyy-mm-dd" as a local date; new Date(str) would read it as UTC midnight
  const parseDate = s => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
  const daysBetween = (a, b) => Math.round((parseDate(b) - parseDate(a)) / 86400000);
  const CODES = {
    state: ["대출가능", "대출중", "예약중", "연체중", "분실", "파손", "기증", "대출불가", "폐기"],
    userState: ["정상", "연체중", "대출중지"],
    bookIn: ["구매", "기증", "비매"],
  };
  const LENT_STATES = ["대출중", "연체중"];

  // The settings shown in this install's 환경설정 screenshots
  function defaultSettings() {
    return {
      // 도서관 설정 (LIBRARY table)
      library: { name: "HKMCC", phone: "408-734-9721", address: "1523 Mclaughlin Ave. San Jose, CA 95",
        email: "www.sjkoreancatholic.org" },
      // 대출환경설정 (LENT_OPTION). delay: 0 적용안함, 1 대출정지부여, 2 연체금납부;
      // delayBasis: 0 가장 큰 연체일 기준, 1 연체일 누적; extend: 0 연장불가, 1 대출일 비례, 2 일괄적용
      lend: { includeLentDay: false, attach: true, relentConfirm: true, relentBan: false, relentDays: 1,
        delay: 0, delayBasis: 0, delayCharge: 100, delayChargeMax: 5000, delayLent: true, chargeSuspend: true,
        extend: 1, extendDays: 1, extendMax: 10, reserve: 1, reserveDays: 3, reserveMax: 3,
        // 휴관일설정: weekdays (0 = 일요일) and fixed dates; due dates skip them
        closedWeekdays: [], closedDates: [] },
      // 회원등급설정: byGrade = 회원등급별로 회원번호 사용(구분기호 사용)
      userCodeByGrade: false,
      grades: [
        { code: 0, name: "Child", prefix: "AA", lendDays: 21, maxLend: 5, maxReserve: 3 },
        { code: 1, name: "Adult", prefix: "AB", lendDays: 21, maxLend: 5, maxReserve: 3 },
        { code: 2, name: "Admin", prefix: "AD", lendDays: 21, maxLend: 5, maxReserve: 3 },
        { code: 3, name: "Premium", prefix: "PR", lendDays: 21, maxLend: 5, maxReserve: 3 },
      ],
      // 도서관리설정: authorCode options as in authorCode.js; isbnSearch 0 기본, 1 국립중앙도서관
      book: { authorCode: { table: 5, authorInitial: false, titleInitial: true, moum: true },
        useSeriesTitle: true, showPublisher: false, isbnSearch: 0,
        locations: [{ code: 1, name: "서가" }, { code: 2, name: "작가별" }, { code: 3, name: "참고" }] },
      // 독서통장 설정
      bankbook: { enabled: true, port: "", library: "HKMCC", address: "1523 Mclaughlin Ave. San Jose, CA 95",
        phone: "408-734-9721", homepage: "", time1: "", time2: "", time3: "", greeting: false, greetingText: "" },
      // 회원증 출력: the 이용안내 on the card back and CLIB.exe.Config CARD_* margins
      card: { title: "이  용  안  내",
        notice: "1. 도서 대출/반납시에는 회원증을 지참합니다.\n2. 도서대출은 1인 5권 21일간으로 합니다.\n3. 본 증은 타인에게 양도할 수 없습니다.\n4. 열람증 분실시에는 본 도서관으로 문의합니다.",
        leftMargin: 20, topMargin: 35, outline: false },
      // 청구기호 출력: CLIB.exe.Config CLAIM_* (label 0 = 3X2.6 cm, 1 = 3X3.1 cm; font 0 = 고딕, 1 = 굴림)
      claim: { label: 1, outline: false, align: "left", barcode: false, leftMargin: 9, topMargin: 23, skip: 0,
        font: 0, fontSize: 10, v: true, c: true, vUpper: true, cUpper: true },
    };
  }

  function claimOf(b) {
    return [b.exCate, `${b.category}-${b.authorCode}`, b.claimVolume && `v.${b.claimVolume}`, b.copy && `c.${b.copy}`]
      .filter(Boolean).join(" ");
  }

  // ISO 2709 from a book's fields, laid out like the record BookManage.NewMarc() starts from
  // (lengths in UTF-8 bytes here; CLIB counts CP949 bytes)
  function isoRecord(r) {
    const FT = "\x1e", SF = "\x1f", RT = "\x1d";
    const now = new Date();
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1, 2)}${pad(now.getDate(), 2)}${pad(now.getHours(), 2)}${pad(now.getMinutes(), 2)}${pad(now.getSeconds(), 2)}`;
    const sub = (ind, pairs) => {
      const body = pairs.filter(([, v]) => v).map(([c, v]) => `${SF}${c}${v}`).join("");
      return body ? ind + body : null;
    };
    const price = r.price && `\\${r.price}`;
    const fields = [
      ["005", stamp],
      ["008", `${stamp.slice(2, 8)}s${(r.year || "").padEnd(4).slice(0, 4)}    ulka          000a  kor  `],
      ["020", sub("  ", [["a", r.isbn], ["c", price]])],
      ["049", sub("0 ", [["l", r.barcode], ["v", r.claimVolume], ["c", r.copy], ["f", r.exCate]])],
      ["056", sub("  ", [["a", r.category]])],
      ["090", sub("  ", [["a", r.category], ["b", r.authorCode], ["c", r.claimVolume]])],
      ["100", sub("1 ", [["a", r.author]])],
      ["245", sub("00", [["a", r.title], ["n", r.volume], ["d", r.author]])],
      ["260", sub("  ", [["a", r.pubPlace], ["b", r.publisher], ["c", r.year]])],
      ["300", sub("  ", [["a", r.pages], ["c", r.size], ["e", r.attach]])],
      ["440", sub("00", [["a", r.seriesTitle], ["v", r.seriesTitle && r.claimVolume]])],
      ["950", sub("0 ", [["b", price]])],
    ].filter(([, body]) => body);
    const size = str => new TextEncoder().encode(str).length;
    let directory = "", data = "", pos = 0;
    for (const [tag, body] of fields) {
      directory += `${tag}${pad(size(body + FT), 4)}${pad(pos, 5)}`;
      pos += size(body + FT);
      data += body + FT;
    }
    directory += FT;
    data += RT;
    const base = 24 + directory.length;
    return `${pad(base + size(data), 5)}nam a22${pad(base, 5)} k 4500${directory}${data}`;
  }

  function makeLibrary() {
    const rnd = seeded("library");
    const today = new Date();
    const settings = defaultSettings();
    const authorCode = (a, t) => window.CLIB.authorCode(a, t, settings.book.authorCode);
    const gradeOf = name => settings.grades.find(g => g.name === name) || settings.grades[0];

    // Due date: the grade's loan days (counting the loan day itself if 대출일 포함하기),
    // moved past closed days (휴관일)
    function dueDate(from, days) {
      let d = addDays(from, days - (settings.lend.includeLentDay ? 1 : 0));
      for (let i = 0; i < 60 && (settings.lend.closedWeekdays.includes(d.getDay()) ||
        settings.lend.closedDates.includes(fmt(d))); i++) d = addDays(d, 1);
      return fmt(d);
    }

    const users = new Map();
    let n = 0;
    for (const [grade, count] of [["Child", 10], ["Adult", 15], ["Admin", 2], ["Premium", 3]]) {
      const g = gradeOf(grade);
      for (let i = 1; i <= count; i++, n++) {
        const id = `${g.prefix}${pad(i, 4)}`;
        users.set(id, {
          userId: id, userName: NAMES[n % NAMES.length], userGrade: grade, userState: "정상",
          phone: `010-${pad(int(rnd, 0, 9999), 4)}-${pad(int(rnd, 0, 9999), 4)}`, address: pick(rnd, ADDRS),
          memo: "", unpaid: 0, suspendUntil: "", email: `user${n + 1}@example.com`,
          regDate: fmt(addDays(today, -int(rnd, 10, 700))),
        });
      }
    }
    Object.assign(users.get("AB0003"), { userState: "대출중지", suspendUntil: fmt(addDays(today, 5)) });
    users.get("AA0001").memo = "보호자 연락처 확인 필요";

    const books = new Map();
    for (let i = 1; i <= 120; i++) {
      const author = pick(rnd, AUTHORS);
      const title = TITLES[(i - 1) % TITLES.length];
      const barcode = `EM${pad(i, 6)}`;
      const book = {
        barcode, isbn: `97911${pad(int(rnd, 0, 99999999), 8)}`, seriesTitle: "", title, volume: "",
        author, pubPlace: pick(rnd, ["서울", "파주", "고양"]), year: String(int(rnd, 2008, 2025)),
        publisher: pick(rnd, PUBLISHERS), pages: `${int(rnd, 32, 640)}p.`, size: `${pick(rnd, [19, 21, 23, 26])}cm`,
        price: String(int(rnd, 8, 38) * 1000), attach: i % 15 === 0 ? pick(rnd, ["CD 1매", "부록 1책", "DVD 1매"]) : "",
        location: ["서가", "서가", "작가별", "참고"][i % 4], bookIn: i % 6 === 0 ? "기증" : "구매",
        state: i % 37 === 0 ? "분실" : i % 29 === 0 ? "파손" : "대출가능",
        uid: i % 3 === 0 ? `E00401${pad((i * 7919).toString(16).toUpperCase(), 10)}` : "",
        exCate: i % 11 === 0 ? "아" : "", category: `${int(rnd, 0, 9)}${int(rnd, 0, 9)}${int(rnd, 0, 9)}.${int(rnd, 1, 9)}`,
        authorCode: authorCode(author, title) || author[0], claimVolume: "", copy: "",
        regDate: fmt(addDays(today, -int(rnd, 30, 900))), modDate: "", queue: [],
      };
      book.modDate = book.regDate;
      books.set(barcode, book);
    }

    const photos = new Map(); // userId -> object URL of a photo picked in 회원관리
    const loans = new Map(); // barcode -> loan
    let next = 40;
    for (const user of users.values()) {
      for (let k = int(rnd, 0, 2); k > 0; k--, next++) {
        const book = books.get(`EM${pad(next, 6)}`);
        if (!book || book.state !== "대출가능") continue;
        const lent = addDays(today, -int(rnd, 1, 30));
        loans.set(book.barcode, { barcode: book.barcode, userId: user.userId, lentDate: fmt(lent),
          dueDate: dueDate(lent, gradeOf(user.userGrade).lendDays), extended: 0, withAttach: !!book.attach });
        book.state = "대출중";
      }
    }
    // EM000010 is back and held for AA0004; EM000041 is out on loan with AA0005 waiting
    Object.assign(books.get("EM000010"), { state: "예약중", queue: ["AA0004"], holdUntil: fmt(addDays(today, 2)) });
    if (loans.has("EM000041")) books.get("EM000041").queue.push("AA0005");

    // RENTAL_HISTORY: { date, barcode, userId, kind: 대출 | 반납 | 연체 }
    const history = [];
    const allUserIds = [...users.keys()];
    for (let d = 120; d >= 1; d--) {
      for (let k = int(rnd, 0, 6); k > 0; k--) {
        const barcode = `EM${pad(int(rnd, 1, 120), 6)}`;
        const userId = pick(rnd, allUserIds);
        history.push({ date: fmt(addDays(today, -d - int(rnd, 3, 14))), barcode, userId, kind: "대출" });
        history.push({ date: fmt(addDays(today, -d)), barcode, userId, kind: "반납" });
        if (rnd() < 0.15) history.push({ date: fmt(addDays(today, -d)), barcode, userId, kind: "연체" });
      }
    }
    for (const l of loans.values()) history.push({ date: l.lentDate, barcode: l.barcode, userId: l.userId, kind: "대출" });
    // 삭제한 회원번호관리: deleted members (USERS.DELETE_YN='Y') keep their history until it is cleared
    const time = d => `${pad(d.getHours(), 2)}:${pad(d.getMinutes(), 2)}:${pad(d.getSeconds(), 2)}`;
    const stamp = () => `${fmt(new Date())}, ${time(new Date())}`; // CLIB's MOD_DATE "yyyy-MM-dd, HH:mm:ss"
    const deleted = [];
    for (const [id, name, grade, ago, books] of [["AB0016", "문지아", "Adult", 40, 3], ["AA0011", "배서준", "Child", 12, 0]]) {
      for (let k = 0; k < books; k++) {
        const barcode = `EM${pad(70 + k, 6)}`;
        history.push({ date: fmt(addDays(today, -ago - 60 + k * 9)), barcode, userId: id, kind: "대출" });
        history.push({ date: fmt(addDays(today, -ago - 50 + k * 9)), barcode, userId: id, kind: "반납" });
      }
      deleted.push({ userId: id, userName: name, userGrade: grade, userState: "정상", phone: "", address: "", memo: "",
        unpaid: 0, suspendUntil: "", email: "", regDate: fmt(addDays(today, -ago - 200)),
        deleteDate: `${fmt(addDays(today, -ago))}, 10:12:00` });
    }
    history.sort((a, b) => a.date.localeCompare(b.date));

    const key = v => String(v ?? "").trim().toUpperCase();
    const userLoans = id => [...loans.values()].filter(l => l.userId === id);
    const loanState = l => (l.dueDate < fmt(new Date()) ? "연체중" : "대출중");
    const reservationsOf = id => [...books.values()].filter(b => b.queue.includes(id));
    const bookView = b => {
      const loan = loans.get(b.barcode);
      return { ...b, queue: [...b.queue], claim: claimOf(b),
        state: loan ? loanState(loan) : b.state,
        loan: loan ? { ...loan, state: loanState(loan), user: { ...users.get(loan.userId) },
          userName: users.get(loan.userId).userName } : null };
    };
    const reserverText = id => `예약회원 : ${id}\n이름 : ${users.get(id).userName}`;
    // A suspension ends by itself on its date
    const refreshState = u => {
      if (u.userState === "대출중지" && u.suspendUntil && u.suspendUntil < fmt(new Date())) {
        Object.assign(u, { userState: "정상", suspendUntil: "" });
      }
    };

    return {
      codes: { ...CODES, get location() { return settings.book.locations.map(l => l.name); } },
      settings,
      today: () => fmt(new Date()),
      claimOf,
      gradeOf,
      authorCode,

      findUser(id) {
        const user = users.get(key(id));
        if (!user) return null;
        refreshState(user);
        const g = gradeOf(user.userGrade);
        const list = userLoans(user.userId).map(l => ({ ...l, book: bookView(books.get(l.barcode)), state: loanState(l) }));
        const reserved = reservationsOf(user.userId).map(b => ({ book: bookView(b), position: b.queue.indexOf(user.userId) + 1 }));
        const memo = [user.memo, user.suspendUntil ? `대출정지일 : ${user.suspendUntil} 까지` : ""].filter(Boolean).join("\n");
        return { ...user, memo, lendDays: g.lendDays, maxLend: g.maxLend, maxReserve: g.maxReserve,
          loans: list, lentCount: list.length, overdue: list.some(l => l.state === "연체중"),
          reservations: reserved, reserveCount: reserved.length };
      },
      findUsers(ids) {
        return ids.map(id => this.findUser(id)).filter(Boolean);
      },
      findUsersByName(name) {
        return [...users.values()].filter(u => u.userName === String(name).trim());
      },
      findBook(barcode) {
        const book = books.get(key(barcode));
        return book ? bookView(book) : null;
      },
      findBooks(barcodes) {
        return barcodes.map(b => this.findBook(b)).filter(Boolean);
      },
      allBooks: () => [...books.values()].map(bookView),
      allLoans: () => [...loans.values()].map(l => ({ ...l, state: loanState(l), book: bookView(books.get(l.barcode)), user: { ...users.get(l.userId) } })),
      allReservations: () => [...books.values()].flatMap(b => b.queue.map((id, i) =>
        ({ book: bookView(b), user: { ...users.get(id) }, position: i + 1, holdUntil: i === 0 ? b.holdUntil || "" : "" }))),

      // Returns { error } | { confirm, title, ask } | { ok, loan }.
      // Each question is asked once; call again with the answers in opts (attach, relend).
      lend(userId, barcode, opts = {}) {
        const L = settings.lend;
        const user = this.findUser(userId);
        if (!user) return { error: "해당하는 회원이 없습니다." };
        const book = books.get(key(barcode));
        if (!book) return { error: "해당하는 도서가 없습니다." };
        if (book.state === "예약중" && book.queue[0] !== user.userId) {
          return { error: `예약중인 도서입니다.\n${reserverText(book.queue[0])}` };
        }
        if (book.state !== "대출가능" && book.state !== "예약중") return { error: `${bookView(book).state} 도서입니다.` };
        if (user.userState !== "정상") return { error: `${user.userState} 회원입니다.` };
        if (!L.delayLent && user.overdue) return { error: "연체중 회원입니다." };
        if (user.lentCount >= user.maxLend) return { error: "최대 대출권수만큼 대출중인 회원입니다." };
        // 반납 후 바로 대출 금지 (동일 도서)
        const lastReturn = [...history].reverse().find(h => h.kind === "반납" && h.barcode === book.barcode && h.userId === user.userId);
        if (L.relentBan && lastReturn) {
          const until = fmt(addDays(parseDate(lastReturn.date), L.relentDays - 1));
          if (until >= fmt(new Date())) return { error: `동일 도서 대출 금지기간입니다.\n${until} 까지` };
        }
        // 재대출 관리: 확인 후 대출
        if (L.relentConfirm && opts.relend === undefined &&
            history.some(h => h.kind === "대출" && h.barcode === book.barcode && h.userId === user.userId)) {
          return { confirm: "해당 회원이 대출했던 도서입니다.\n다시 대출하시겠습니까?", title: "도서대출", ask: "relend" };
        }
        if (opts.relend === false) return { cancelled: true };
        // 딸림자료 대출관리
        if (L.attach && book.attach && opts.attach === undefined) {
          return { confirm: `딸림자료 : ${book.attach}\n딸림자료가 있는 도서입니다.\n함께 대출하시겠습니까?`, title: "딸림자료대출", ask: "attach" };
        }
        const now = new Date();
        const loan = { barcode: book.barcode, userId: user.userId, lentDate: fmt(now),
          dueDate: dueDate(now, user.lendDays), extended: 0, withAttach: L.attach && !!opts.attach };
        loans.set(book.barcode, loan);
        history.push({ date: loan.lentDate, barcode: book.barcode, userId: user.userId, kind: "대출" });
        if (book.queue[0] === user.userId) { book.queue.shift(); book.holdUntil = ""; }
        book.state = "대출중";
        return { ok: true, loan };
      },

      // ExtendBook(): 대출일 비례 = the grade's loan days x the factor, 일괄적용 = fixed days
      extend(barcode) {
        const L = settings.lend;
        if (!books.has(key(barcode))) return { error: "해당하는 도서가 없습니다." };
        const loan = loans.get(key(barcode));
        if (!loan) return { error: "대출중인 도서가 아닙니다." };
        if (L.extend === 0) return { error: "[연장불가] 상태입니다.\n연장을 허용하시려면 [대출환경설정]에서\n[연장관리] 옵션을 설정해주세요." };
        if (loanState(loan) === "연체중") return { error: "연체중인 도서입니다." };
        if (loan.extended >= L.extendMax) return { error: "최대 연장횟수만큼 연장된 도서입니다." };
        const days = L.extend === 1 ? gradeOf(users.get(loan.userId).userGrade).lendDays * L.extendDays : L.extendDays;
        loan.dueDate = dueDate(parseDate(loan.dueDate), days + (L.includeLentDay ? 1 : 0));
        loan.extended++;
        return { ok: true, loan, message: `연장되었습니다.\n반납예정일 : ${loan.dueDate}` };
      },

      // ReturnBook(): returns { error } | { confirm, title } | { ok, userId, messages }.
      // A loan that took its 딸림자료 asks first; call again with { attach: true|false }.
      returnBook(barcode, opts = {}) {
        const L = settings.lend;
        const book = books.get(key(barcode));
        if (!book) return { error: "해당하는 도서가 없습니다." };
        const loan = loans.get(book.barcode);
        if (!loan) return { error: "대출중인 도서가 아닙니다." };
        if (loan.withAttach && opts.attach === undefined) {
          return { confirm: "딸림자료가 함께 대출되었습니다.\n딸림자료도 반납하시겠습니까?", title: "딸림자료 반납", ask: "attach" };
        }
        const messages = [];
        const late = daysBetween(loan.dueDate, fmt(new Date()));
        const user = users.get(loan.userId);
        loans.delete(book.barcode);
        history.push({ date: fmt(new Date()), barcode: book.barcode, userId: loan.userId, kind: "반납" });
        if (late > 0) {
          history.push({ date: fmt(new Date()), barcode: book.barcode, userId: loan.userId, kind: "연체" });
          if (L.delay === 1) {
            // 대출정지부여: from today (가장 큰 연체일 기준) or added to an existing suspension (누적)
            const base = L.delayBasis === 1 && user.suspendUntil > fmt(new Date()) ? parseDate(user.suspendUntil) : new Date();
            const until = fmt(addDays(base, late));
            if (L.delayBasis === 1 || !user.suspendUntil || until > user.suspendUntil) user.suspendUntil = until;
            user.userState = "대출중지";
            messages.push(`연체된 도서입니다.\n해당 회원은 다음 기간까지 대출정지됩니다.\n대출정지기간 : ${user.suspendUntil}까지`);
          } else if (L.delay === 2) {
            const fee = late * L.delayCharge;
            user.unpaid = Math.min(L.delayChargeMax, user.unpaid + fee);
            if (L.chargeSuspend) {
              user.userState = "대출중지";
              messages.push(`연체된 도서입니다.\n연체금 납부시까지 대출정지됩니다.\n연체금 : ${fee} 원\n 총 연체금액 : ${user.unpaid} 원`);
            } else {
              messages.push(`연체된 도서입니다.\n연체금 : ${fee} 원\n 총 연체금액 : ${user.unpaid} 원`);
            }
          }
        }
        if (book.queue.length) {
          book.state = "예약중";
          book.holdUntil = fmt(addDays(new Date(), L.reserveDays));
          messages.push(`예약된 회원이 있습니다.\n${reserverText(book.queue[0])}`);
        } else {
          book.state = "대출가능";
        }
        return { ok: true, userId: loan.userId, messages };
      },

      // ReserveBook(): returns { error } | { ok }
      reserve(userId, barcode) {
        const L = settings.lend;
        if (L.reserve === 0) return { error: "[예약불가] 상태입니다.\n예약을 사용하시려면 [대출반납설정]에서\n[예약관리]를 설정해주세요" };
        const user = this.findUser(userId);
        if (!user) return { error: "해당하는 회원이 없습니다." };
        const book = books.get(key(barcode));
        if (!book) return { error: "해당하는 도서가 없습니다." };
        const state = bookView(book).state;
        if (![...LENT_STATES, "예약중"].includes(state)) return { error: "대출중, 연체중, 예약중인 도서만 예약 할 수 있습니다." };
        if (user.userState !== "정상") return { error: `${user.userState} 회원입니다.` };
        const loan = loans.get(book.barcode);
        if (loan && loan.userId === user.userId) return { error: "해당 도서 대출자입니다." };
        if (book.queue.includes(user.userId)) return { error: "이미 해당 도서를 예약중인 회원입니다." };
        if (user.reserveCount >= user.maxReserve) return { error: "최대 예약권수만큼 예약중인 회원입니다." };
        if (book.queue.length >= L.reserveMax) {
          return { error: `예약 대기자가 최대인 도서입니다.\n최대 대기자수 : ${L.reserveMax} 명\n현재 대기자수 : ${book.queue.length} 명` };
        }
        book.queue.push(user.userId);
        return { ok: true };
      },

      cancelReserve(userId, barcode) {
        const book = books.get(key(barcode));
        if (!book) return { error: "해당하는 도서가 없습니다." };
        const i = book.queue.indexOf(key(userId));
        if (i < 0) return { error: "해당 도서를 예약중인 회원이 아닙니다." };
        book.queue.splice(i, 1);
        if (book.state === "예약중" && !book.queue.length) { book.state = "대출가능"; book.holdUntil = ""; }
        return { ok: true, message: "예약이 취소되었습니다" };
      },

      // SearchMarc: field is one of the 검색기준 labels
      searchBooks({ field, keyword, from, to, start, end }) {
        const FIELDS = { 서명: "title", 등록번호: "barcode", 총서명: "seriesTitle", 저자: "author",
          저자기호: "authorCode", ISBN: "isbn", 출판사: "publisher", 분류기호: "category", 별치기호: "exCate",
          도서상태: "state", 소장위치: "location", 반입구분: "bookIn", 등록일: "regDate" };
        const all = this.allBooks();
        if (start !== undefined) {
          const lo = key(start) || "", hi = key(end) || "￿";
          return all.filter(b => b.barcode >= lo && b.barcode <= hi);
        }
        const f = FIELDS[field] || "title";
        if (f === "regDate") return all.filter(b => (!from || b.regDate >= from) && (!to || b.regDate <= to));
        const kw = String(keyword || "").trim().toLowerCase();
        return all.filter(b => String(b[f] || "").toLowerCase().includes(kw));
      },
      exCategories: () => [...new Set([...books.values()].map(b => b.exCate).filter(Boolean))],

      // 도서관리 저장. Field checks happen in the screen; this checks loans and duplicates.
      // Returns { error } | { confirm, title } | { ok, book }. Pass { overwrite: true } after a confirm.
      saveBook(record, opts = {}) {
        const barcode = key(record.barcode);
        const existing = books.get(barcode);
        const original = opts.originalBarcode ? books.get(key(opts.originalBarcode)) : null;
        if (existing && existing !== original && !opts.overwrite) {
          return { confirm: "동일한 등록번호의 도서가 있습니다.\n정보를 덮어쓰기 하시겠습니까?", title: "등록번호 중복" };
        }
        const target = original || existing;
        if (target && loans.has(target.barcode) && !LENT_STATES.includes(record.state)) {
          return { error: "대출자가 있는 도서입니다.\n반납처리를 하신 후 상태를 변경해주세요." };
        }
        if (target && target.queue.length && record.state !== target.state && record.state !== "예약중") {
          return { error: "예약자가 있는 도서입니다.\n예약취소를 하신 후 상태를 변경해주세요." };
        }
        if (original && original.barcode !== barcode) books.delete(original.barcode);
        const book = { ...(target || { regDate: fmt(new Date()), queue: [], uid: "" }), ...record, barcode, modDate: fmt(new Date()) };
        // While on loan the stored state stays 대출중; the view derives 연체중 from the due date
        if (loans.has(barcode)) book.state = "대출중";
        books.set(barcode, book);
        return { ok: true, book: bookView(book) };
      },

      deleteBook(barcode) {
        const book = books.get(key(barcode));
        if (!book) return { error: "해당하는 도서가 없습니다." };
        if (loans.has(book.barcode)) return { error: "현재 대출중인 도서입니다.\n도서를 반납 후 삭제해주세요." };
        if (book.queue.length) return { error: "현재 예약중인 도서입니다.\n예약을 취소 후 삭제해주세요." };
        books.delete(book.barcode);
        return { ok: true };
      },

      // ---- members (Users.cs, UserSearch.cs) ----
      get grades() { return settings.grades.map(g => ({ ...g, grade: g.name })); },
      // 회원등급별로 회원번호 사용: the grade's 구분기호 + 4 digits; otherwise one shared sequence
      nextUserId(grade) {
        const prefix = settings.userCodeByGrade ? gradeOf(grade).prefix : "";
        const used = [...users.keys(), ...deleted.map(u => u.userId)].filter(id => id.startsWith(prefix) && /^\d+$/.test(id.slice(prefix.length)))
          .map(id => parseInt(id.slice(prefix.length), 10));
        return `${prefix}${pad(Math.max(0, ...used) + 1, prefix ? 4 : 6)}`;
      },
      // UserSearch: field is one of the 검색구분 labels
      searchUsers(field, keyword) {
        const FIELDS = { 회원번호: "userId", 회원명: "userName", 회원등급: "userGrade", 회원상태: "userState",
          주소: "address", 전화번호: "phone", 이메일: "email" };
        const f = FIELDS[field] || "userId";
        const kw = String(keyword || "").trim().toLowerCase();
        return [...users.keys()].map(id => this.findUser(id))
          .filter(u => String(u[f] || "").toLowerCase().includes(kw));
      },
      // Users.SaveUsers(), as the server does it: { error } | { confirm, title, ask } | { cancelled }
      // | { ok, user }. A number left by a deleted member asks before it is reused (its old
      // history goes); a new member's number already in use asks before overwriting.
      saveUser(record, answers = {}) {
        const id = key(record.userId);
        if (!id) return { error: "회원번호를 입력해주세요." };
        if (!/^[A-Z0-9]+$/.test(id)) return { error: "회원번호는 영어와 숫자만 가능합니다." };
        if (!String(record.userName || "").trim()) return { error: "회원명을 입력해주세요." };
        if (!settings.grades.some(g => g.name === String(record.userGrade || "").trim())) return { error: "회원등급이 잘못되었습니다." };
        if (deleted.some(u => u.userId === id)) {
          if (!("deletedCode" in answers)) {
            return { confirm: "삭제된 회원번호입니다.\n이전 기록을 삭제 후 사용하시겠습니까?\n※ 이전 기록을 삭제 후 회원번호를 재사용하는 경우,\n삭제된 기록은 복구할 수 없습니다.",
              title: "회원번호 재사용", ask: "deletedCode" };
          }
          if (!answers.deletedCode) return { cancelled: true };
        }
        if (users.has(id) && record.isNew) {
          if (!("overwrite" in answers)) return { confirm: "동일한 회원번호가 이미 존재합니다.\n덮어쓰겠습니까?", title: "회원번호중복", ask: "overwrite" };
          if (!answers.overwrite) return { cancelled: true };
        }
        if (answers.deletedCode) {
          for (let i = deleted.length - 1; i >= 0; i--) if (deleted[i].userId === id) deleted.splice(i, 1);
          for (let i = history.length - 1; i >= 0; i--) if (history[i].userId === id) history.splice(i, 1);
        }
        const { memo, isNew, ...rest } = record;
        const prev = users.get(id) || { unpaid: 0, suspendUntil: "", regDate: fmt(new Date()) };
        // The memo box also shows the suspension line; keep only what was typed
        const cleanMemo = String(memo || "").split("\n").filter(l => !l.startsWith("대출정지일 :")).join("\n");
        users.set(id, { ...prev, ...rest, memo: cleanMemo, userId: id,
          userName: String(rest.userName).trim(), userGrade: String(rest.userGrade).trim(),
          // back to 정상 ends a suspension
          ...(rest.userState === "정상" ? { suspendUntil: "" } : {}) });
        return { ok: true, user: this.findUser(id) };
      },
      deleteUser(userId) {
        const user = this.findUser(userId);
        if (!user) return { error: "해당하는 회원이 없습니다." };
        if (user.lentCount) return { error: "현재 대출중인 도서가 있습니다.\n도서를 반납 후 삭제해주세요." };
        if (user.reserveCount) return { error: "현재 예약중인 도서가 있습니다.\n예약을 취소 후 삭제해주세요." };
        deleted.push({ ...users.get(user.userId), deleteDate: stamp() });
        users.delete(user.userId);
        return { ok: true };
      },

      // ---- 등급별 회원번호관리 (UserCodeDlg.cs) ----
      usersByGrade(grade) {
        return [...users.values()].filter(u => u.userGrade === grade).sort((a, b) => a.userId.localeCompare(b.userId))
          .map(u => ({ userGrade: u.userGrade, userId: u.userId, userName: u.userName }));
      },
      // ReUserCode(): the grade's 구분기호 and the next number; the member's loans, reservations
      // and history move to it. Asks first unless answers.renumber is set.
      renumberUser(userId, grade, answers = {}) {
        const user = users.get(key(userId));
        if (!user) return { error: "해당하는 회원이 없습니다." };
        const prefix = gradeOf(grade).prefix;
        const nums = [...users.keys(), ...deleted.map(u => u.userId)]
          .filter(id => id.startsWith(prefix) && /^\d+$/.test(id.slice(prefix.length)))
          .map(id => [parseInt(id.slice(prefix.length), 10), id.length - prefix.length]);
        const [top, width] = nums.reduce((a, b) => (b[0] > a[0] ? b : a), [0, 8]);
        const next = `${prefix}${pad(top + 1, width)}`;
        if (answers.renumber === undefined) {
          return { confirm: `회원번호를 변경하시겠습니까?\n기존 : ${user.userId}\n변경 : ${next}`, title: "회원번호", ask: "renumber" };
        }
        if (!answers.renumber) return { cancelled: true };
        users.delete(user.userId);
        users.set(next, { ...user, userId: next });
        for (const l of loans.values()) if (l.userId === user.userId) l.userId = next;
        for (const b of books.values()) b.queue = b.queue.map(id => (id === user.userId ? next : id));
        for (const h of history) if (h.userId === user.userId) h.userId = next;
        return { ok: true, userId: next };
      },

      // ---- 삭제한 회원번호관리 (DeleteUsers.cs) ----
      // Counts only the history up to the deletion, as CLIB does (reg_date <= mod_date)
      deletedUsers() {
        return [...deleted].sort((a, b) => a.deleteDate.localeCompare(b.deleteDate)).map(u => {
          const until = u.deleteDate.replace(",", "");
          const count = kind => history.filter(h => h.userId === u.userId && h.kind === kind && h.date <= until).length;
          return { userId: u.userId, userName: u.userName, deleteDate: u.deleteDate,
            lent: count("대출"), returned: count("반납"), overdue: count("연체") };
        });
      },
      // DeleteUserCode(): the deleted member and its history up to the deletion are gone for good
      purgeUser(userId, deleteDate) {
        const until = String(deleteDate).replace(",", "");
        for (let i = deleted.length - 1; i >= 0; i--) if (deleted[i].userId === userId) deleted.splice(i, 1);
        for (let i = history.length - 1; i >= 0; i--) if (history[i].userId === userId && history[i].date <= until) history.splice(i, 1);
        return { ok: true };
      },
      // ReUseUserCode(): back to the member list, unless someone else has the number now
      restoreUser(userId) {
        if (users.has(userId)) return { error: "이미 해당번호를 다른 회원이 사용중입니다." };
        const i = deleted.findIndex(u => u.userId === userId);
        if (i < 0) return { error: "해당하는 회원이 없습니다." };
        const [{ deleteDate, ...user }] = deleted.splice(i, 1);
        users.set(userId, user);
        return { ok: true };
      },

      // ---- 연체관리 (BookDelay.cs) ----
      // Members who are 연체중 and the loans past their due date. The sample library doesn't
      // keep a 연체중 state, so members with an overdue loan count as 연체중.
      overdue() {
        const late = [...loans.values()].filter(l => loanState(l) === "연체중");
        const lateUsers = new Set(late.map(l => l.userId));
        const person = u => ({ userId: u.userId, userName: u.userName, userGrade: u.userGrade,
          userState: u.userState === "정상" ? "연체중" : u.userState, phone: u.phone, address: u.address,
          email: u.email, unpaid: u.unpaid });
        return {
          users: [...users.values()].filter(u => lateUsers.has(u.userId))
            .map(u => ({ ...person(u), overdueCount: late.filter(l => l.userId === u.userId).length })),
          loans: late.map(l => {
            const b = books.get(l.barcode);
            return { ...person(users.get(l.userId)), barcode: b.barcode, title: b.title, volume: b.volume,
              author: b.author, claim: claimOf(b), bookState: "연체중", lentDate: l.lentDate, dueDate: l.dueDate };
          }),
        };
      },

      // ---- 파일로 저장: Marc 파일 저장 (SaveFileProcess.SaveMarcFileThFn) ----
      // items: [{ record, original, saved }]. The sample library has no stored MARC, so each
      // record is written from its fields, in UTF-8 (CLIB writes CP949).
      marcFile(items, crlf) {
        const records = items.map(it => isoRecord(it.record));
        return { blob: new Blob([records.join(crlf ? "\r\n" : "")], { type: "application/marc" }), count: records.length };
      },
      // 연체금 완납: nothing owed, and 연체중 while books are still overdue, otherwise 정상
      // 회원 사진: kept in the page as the picked file (the server saves it as <회원번호>.<ext>)
      photoUrl: id => photos.get(key(id)) || null,
      savePhoto(id, file) {
        const user = users.get(key(id));
        if (!user) return { error: "회원을 먼저 저장해주세요." };
        if (photos.has(user.userId)) URL.revokeObjectURL(photos.get(user.userId));
        photos.set(user.userId, URL.createObjectURL(file));
        user.photo = file.name;
        return { ok: true, photo: file.name };
      },

      payCharge(userId) {
        const user = users.get(key(userId));
        if (!user) return { error: "해당하는 회원이 없습니다." };
        const late = userLoans(user.userId).some(l => loanState(l) === "연체중");
        Object.assign(user, { unpaid: 0, userState: late ? "연체중" : "정상" }, late ? {} : { suspendUntil: "" });
        return { ok: true };
      },
      // 이용내역 조회 (UserLentStats): the member's RENTAL_HISTORY with each book
      userHistory(userId) {
        const user = users.get(key(userId));
        if (!user) return null;
        const KDC = ["총류", "철학", "종교", "사회과학", "자연과학", "기술과학", "예술", "언어", "문학", "역사"];
        return { userId: user.userId, userName: user.userName, rows: history.filter(h => h.userId === user.userId && books.has(h.barcode)).map(h => {
          const b = books.get(h.barcode);
          return { date: h.date, barcode: h.barcode, title: b.volume ? `${b.title}. ${b.volume}` : b.title,
            category: /^\d/.test(b.category) ? KDC[Number(b.category[0])] : "", state: h.kind };
        }) };
      },

      // 도서보유현황 (by: 0 도서상태, 1 도서분류, 2 별치기호, 3 소장위치, 4 반입구분) and
      // 이용자현황 (by: 0 회원등급, 1 회원상태), in the server's shapes
      bookStats(by) {
        const all = [...books.values()].map(bookView);
        const groups = this.bookGroups(by, all);
        return [{ name: "전체", count: all.length }, ...groups.map(([name, test]) => ({ name, count: all.filter(test).length }))];
      },
      bookStatsDetail(by, name, row) {
        const all = [...books.values()].map(bookView);
        const groups = this.bookGroups(by, all);
        const test = by === 1 ? (groups[row - 1] || [])[1] : (groups.find(([n]) => n === name) || [])[1];
        return all.filter(b => (by === 1 ? row === 0 : name === "전체") || (test && test(b)))
          .sort((a, b) => a.barcode.localeCompare(b.barcode))
          .map((b, i) => ({ no: i + 1, bookState: b.state, barcode: b.barcode, title: b.volume ? `${b.title}. ${b.volume}` : b.title,
            author: b.author, publisher: b.publisher, claim: b.claim, location: b.location, bookIn: b.bookIn, regDate: b.regDate || "" }));
      },
      bookGroups(by, all) {
        const by_ = (key, names) => names.map(n => [n, b => b[key] === n]);
        if (by === 0) return by_("state", CODES.state);
        if (by === 1) return Array.from({ length: 10 }, (_, i) => [["000 : 총류", "100 : 철학", "200 : 종교", "300 : 사회과학",
          "400 : 자연과학", "500 : 기술과학", "600 : 예술", "700 : 언어", "800 : 문학", "900 : 역사"][i],
          b => (b.category || "") >= `${i}00` && (b.category || "") < (i < 9 ? `${i + 1}00` : "999.99999999999")]);
        if (by === 2) return by_("exCate", [...new Set(all.map(b => b.exCate || ""))].sort());
        if (by === 3) return by_("location", settings.book.locations.map(l => l.name));
        return by_("bookIn", CODES.bookIn);
      },
      userStats(by) {
        const all = [...users.values()];
        const names = by === 0 ? settings.grades.map(g => g.name) : CODES.userState;
        const key = by === 0 ? "userGrade" : "userState";
        return { rows: [{ name: "전체", count: all.length }, ...names.map(n => ({ name: n, count: all.filter(u => u[key] === n).length }))] };
      },
      userStatsDetail(by, name) {
        const key = by === 0 ? "userGrade" : "userState";
        const count = (id, kind) => history.filter(h => h.userId === id && h.kind === kind).length;
        return { rows: [...users.values()].filter(u => name === "전체" || u[key] === name)
          .sort((a, b) => a.userId.localeCompare(b.userId))
          .map((u, i) => ({ no: i + 1, userGrade: u.userGrade, userState: u.userState, userId: u.userId, userName: u.userName,
            phone: u.phone, address: u.address, email: u.email, totalLent: count(u.userId, "대출"),
            totalOverdue: count(u.userId, "연체"), suspendUntil: u.suspendUntil || "", regDate: u.regDate || "" })) };
      },

      // RENTAL_HISTORY joined with the book and member, for 대출/반납 통계
      history() {
        return history.map(h => {
          const b = books.get(h.barcode);
          const u = users.get(h.userId);
          return { ...h, title: b ? b.title : "", category: b ? b.category : "",
            userName: u ? u.userName : "", userGrade: u ? u.userGrade : "" };
        });
      },

      // 환경설정 저장: replaces sections of the settings (deep enough for these screens)
      saveSettings(changes) {
        for (const [k, v] of Object.entries(changes)) {
          settings[k] = Array.isArray(v) ? v : v && typeof v === "object" ? { ...settings[k], ...v } : v;
        }
      },
    };
  }

  // Tiny event bus so dialogs can hand results back (도서 불러오기 -> 도서관리)
  const listeners = {};
  window.CLIB = window.CLIB || {};
  window.CLIB.bus = {
    on(name, fn) { (listeners[name] = listeners[name] || new Set()).add(fn); return () => listeners[name].delete(fn); },
    emit(name, payload) { (listeners[name] || []).forEach(fn => fn(payload)); },
  };
  window.CLIB.library = makeLibrary();
  window.CLIB.data = {
    isSample: true,
    getRows(screen, table) {
      const rnd = seeded(`${screen.id}/${table.id}`);
      const rows = Array.from({ length: rowCount(screen, table) },
        (_, i) => makeRow(i, rnd, screen, table));
      const dateCol = table.columns.find(c => c.key === "date");
      if (dateCol && screen.menu === "stats") rows.sort((a, b) => a.date.localeCompare(b.date));
      if (rows.length && "ratio" in rows[0] && "count" in rows[0]) {
        const total = rows.reduce((n, r) => n + r.count, 0);
        rows.forEach(r => { r.ratio = (r.count * 100 / total).toFixed(1); });
      }
      return Promise.resolve(rows);
    },
  };
})();
