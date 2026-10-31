// Connection to the local server (server/app.py). When the page is served by it,
// window.CLIB.server is a library with the same methods as the sample one in data.js,
// backed by CLIB's database. Screens that set `server: true` in their logic use it.
(function () {
  window.CLIB = window.CLIB || {};

  async function post(path, body) {
    const res = await fetch(new URL(`api/${path}`, location.href), {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result && result.error ? result.error : `서버 오류 (${res.status})`);
    return result;
  }

  async function get(path, params) {
    const url = new URL(`api/${path}`, location.href);
    for (const [k, v] of Object.entries(params || {})) if (v !== undefined && v !== null) url.searchParams.set(k, v);
    const res = await fetch(url);
    if (res.status === 404) return null;
    const body = await res.json();
    if (!res.ok) throw new Error(body && body.error ? body.error : `서버 오류 (${res.status})`);
    return body;
  }

  function makeServerLibrary(meta) {
    let db = meta.settings;
    // Start from the sample settings so screens find every field, then use the database's.
    // Kept as one object and refreshed in place after a save, so open screens see new values.
    const sample = window.CLIB.library.settings;
    const settings = {};
    const codes = {};
    function apply(fresh) {
      db = fresh;
      Object.assign(settings, {
        ...sample,
        library: db.library,
        lend: { ...sample.lend, ...db.lend },
        grades: db.grades,
        userCodeByGrade: db.userCodeByGrade,
        book: { ...sample.book, ...db.book, locations: db.locations },
        card: { ...sample.card, ...db.card },
        bankbook: { ...sample.bankbook, ...db.bankbook },
      });
      Object.assign(codes, { ...db.codes, location: db.locations.map(l => l.name) });
    }
    apply(db);
    const gradeOf = name => settings.grades.find(g => g.name === name) || settings.grades[0];
    const enc = encodeURIComponent;

    return {
      isServer: true,
      readOnly: meta.readOnly,
      database: meta.database,
      settings,
      codes,
      get grades() { return settings.grades.map(g => ({ ...g, grade: g.name })); },
      gradeOf,
      today: () => window.CLIB.library.today(),
      claimOf: window.CLIB.library.claimOf,
      authorCode: (a, t) => window.CLIB.authorCode(a, t, settings.book.authorCode),

      findUser: id => get(`users/${enc(String(id).trim())}`),
      // many at once in one request (회원검색 → 불러오기); one request per member crashed LocalDB
      findUsers: ids => post("users/batch", { ids }),
      findUsersByName: name => get("users", { name }),
      searchUsers: (field, q) => get("users", { field, q }),
      // { full: true } adds the MARC fields 도서관리 shows (발행지, 출판년도, 페이지, …) and the MARC text
      findBook: (barcode, opts = {}) => get(`books/${enc(String(barcode).trim())}`, opts.full ? { full: 1 } : null),
      findBooks: (barcodes, opts = {}) => post("books/batch", { barcodes, full: !!opts.full }),
      nextUserId: grade => get("users/next", { grade }),
      // the member's photo (404 when there is none); version makes the browser fetch it again
      photoUrl: (id, version) => `api/users/${enc(id)}/photo${version ? `?v=${version}` : ""}`,
      async savePhoto(id, file) {
        const res = await fetch(new URL(`api/users/${enc(id)}/photo`, location.href), { method: "POST", body: file });
        const result = await res.json();
        if (!res.ok) throw new Error(result && result.error ? result.error : `서버 오류 (${res.status})`);
        return result;
      },
      searchBooks: ({ field, keyword, start, end }) =>
        (start !== undefined ? get("books", { start, end }) : get("books", { field, q: keyword })),
      allLoans: () => get("loans"),
      allReservations: () => get("reservations"),
      history: (from, to) => get("history", { from, to }),
      // 도서보유현황 / 이용자현황: totals [{ name, count }] (전체 first) and the rows behind one
      bookStats: by => get("stats/books", { by }),
      bookStatsDetail: (by, name, row) => get("stats/books/detail", { by, name, row }),
      userStats: by => get("stats/users", { by }),
      userStatsDetail: (by, name) => get("stats/users/detail", { by, name }),
      exCategories: () => db.exCategories,
      // 환경설정 panels and 회원증 출력: { lend, grades, userCodeByGrade, book, bankbook, library, card }
      async saveSettings(changes) {
        const result = await post("settings", { changes });
        if (result.ok) apply(result.settings);
        return result;
      },

      // Written to CLIB's database (server/circulation.py). A question comes back as
      // { confirm, title, ask }; call again with answers[ask] set.
      lend: (userId, barcode, answers = {}) => post("lend", { userId, barcode, answers }),
      returnBook: (barcode, answers = {}) => post("return", { barcode, answers }),
      extend: barcode => post("extend", { barcode }),

      reserve: (userId, barcode) => post("reserve", { userId, barcode }),
      cancelReserve: (userId, barcode) => post("reserve/cancel", { userId, barcode }),

      // record.isNew: the screen was making a new member (asks before overwriting one)
      saveUser: (record, answers = {}) => post("users", { user: record, answers }),
      deleteUser: userId => post("users/delete", { userId }),
      // opts: { originalBarcode, answers }; answers.overwrite / answers.changeCode answer the questions
      saveBook: (record, opts = {}) => post("books", { book: record, original: opts.originalBarcode || null,
        answers: { ...(opts.overwrite ? { overwrite: true } : {}), ...(opts.answers || {}) } }),
      deleteBook: barcode => post("books/delete", { barcode }),

      // 연체관리: { users, loans } (USER_STATE 연체중 members, BOOK_LENT STATS 연체중 loans)
      overdue: () => get("overdue"),
      // 파일로 저장: the checked books' MARC records as one CP949 file. A saved row sends its
      // barcode (the stored record); an edited or new one sends its fields as well.
      async marcFile(items, crlf) {
        const res = await fetch(new URL("api/books/marcfile", location.href), {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ crlf, items: items.map(it => ({ original: it.original || null, record: it.saved ? null : it.record })) }),
        });
        if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
        return { blob: await res.blob(), count: Number(res.headers.get("X-Record-Count")) || 0 };
      },

      // 데이터백업 / 데이터복구 / 자동백업설정 (server/backup.py)
      backups: () => get("backup"),
      backup: () => post("backup", {}),
      backupFileUrl: (folder, name) => `api/backup/file?folder=${enc(folder)}&name=${enc(name)}`,
      async uploadBackup(file) {
        const res = await fetch(new URL(`api/backup/upload?name=${enc(file.name)}`, location.href), { method: "POST", body: file });
        if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
        return res.json();
      },
      restoreBackup: (folder, name) => post("backup/restore", { folder, name }),
      saveBackupOptions: options => post("backup/options", options),

      // 등급별 회원번호관리
      usersByGrade: grade => get("users", { grade }),
      renumberUser: (userId, grade, answers = {}) => post("users/renumber", { userId, grade, answers }),
      // 삭제한 회원번호관리
      deletedUsers: () => get("users/deleted"),
      purgeUser: (userId, deleteDate) => post("users/purge", { userId, deleteDate }),
      restoreUser: userId => post("users/restore", { userId }),

      // 연체금 완납 / 이용내역 조회
      payCharge: userId => post("users/paycharge", { userId }),
      userHistory: userId => get(`users/${enc(String(userId).trim())}/history`),
    };
  }

  // Only try when served over http(s); opening index.html from disk stays on sample data
  window.CLIB.ready = (location.protocol.startsWith("http")
    ? get("meta").catch(() => null)
    : Promise.resolve(null)
  ).then(meta => {
    if (meta) window.CLIB.server = makeServerLibrary(meta);
  });
})();
