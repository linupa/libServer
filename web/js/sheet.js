// Reads the first sheet of an Excel (.xls, .xlsx) or CSV file as rows of text, for
// 회원일괄입력. CLIB opens these through Excel itself; a browser has no Excel, so the formats
// are read here: .xls is BIFF8 inside an OLE2 compound file, .xlsx a zip of XML parts, and
// CSV is UTF-8 or CP949 (what CLIB writes with Encoding.Default).
(function () {
  window.CLIB = window.CLIB || {};

  // ---- CSV ------------------------------------------------------------------------
  function decodeText(bytes) {
    try {
      return new TextDecoder("utf-8", { fatal: true }).decode(bytes).replace(/^﻿/, "");
    } catch {
      return new TextDecoder("euc-kr").decode(bytes); // WHATWG euc-kr is CP949
    }
  }
  function parseCsv(text) {
    const rows = [];
    let row = [], cell = "", quoted = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (ch === '"') quoted = false;
        else cell += ch;
      } else if (ch === '"') quoted = true;
      else if (ch === ",") { row.push(cell); cell = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(cell); rows.push(row); row = []; cell = "";
      } else cell += ch;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    return rows;
  }

  // A number cell as Excel's Value2.ToString() shows it (1012345678, 3.5)
  const numText = n => (Number.isInteger(n) ? String(n) : String(Number(n.toPrecision(15))));
  function place(rows, r, c, value) {
    (rows[r] = rows[r] || [])[c] = value;
  }
  const dense = rows => Array.from(rows, r => Array.from(r || [], v => v ?? ""));

  // ---- .xlsx: zip + XML ---------------------------------------------------------------
  async function inflate(data) {
    const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }
  async function unzip(bytes) {
    const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    let eocd = bytes.length - 22;
    while (eocd >= 0 && v.getUint32(eocd, true) !== 0x06054b50) eocd--;
    if (eocd < 0) throw new Error("zip");
    const count = v.getUint16(eocd + 10, true);
    let p = v.getUint32(eocd + 16, true);
    const files = {};
    for (let i = 0; i < count; i++) {
      const method = v.getUint16(p + 10, true), size = v.getUint32(p + 20, true);
      const nameLen = v.getUint16(p + 28, true), extra = v.getUint16(p + 30, true), comment = v.getUint16(p + 32, true);
      const local = v.getUint32(p + 42, true);
      const name = new TextDecoder().decode(bytes.subarray(p + 46, p + 46 + nameLen));
      const start = local + 30 + v.getUint16(local + 26, true) + v.getUint16(local + 28, true);
      files[name] = { method, data: bytes.subarray(start, start + size) };
      p += 46 + nameLen + extra + comment;
    }
    return async name => {
      const f = files[name];
      if (!f) return null;
      const raw = f.method === 8 ? await inflate(f.data) : f.data;
      return new DOMParser().parseFromString(new TextDecoder().decode(raw), "application/xml");
    };
  }
  const tags = (doc, name) => [...doc.getElementsByTagNameNS("*", name)];
  async function readXlsx(bytes) {
    const open = await unzip(bytes);
    // The first sheet in the workbook, through its relationship
    let path = "xl/worksheets/sheet1.xml";
    const book = await open("xl/workbook.xml"), rels = await open("xl/_rels/workbook.xml.rels");
    const sheet = book && tags(book, "sheet")[0];
    const id = sheet && (sheet.getAttribute("r:id") || sheet.getAttributeNS("http://schemas.openxmlformats.org/officeDocument/2006/relationships", "id"));
    const rel = rels && tags(rels, "Relationship").find(r => r.getAttribute("Id") === id);
    if (rel) path = rel.getAttribute("Target").replace(/^\/?(xl\/)?/, "xl/");
    const shared = await open("xl/sharedStrings.xml");
    const strings = shared ? tags(shared, "si").map(si => tags(si, "t").map(t => t.textContent).join("")) : [];
    const doc = await open(path);
    if (!doc) throw new Error("sheet");
    const rows = [];
    for (const c of tags(doc, "c")) {
      const ref = /^([A-Z]+)(\d+)$/.exec(c.getAttribute("r") || "");
      if (!ref) continue;
      const col = [...ref[1]].reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0) - 1;
      const v = tags(c, "v")[0], type = c.getAttribute("t");
      let value = "";
      if (type === "s") value = strings[Number(v && v.textContent)] ?? "";
      else if (type === "inlineStr") value = tags(c, "t").map(t => t.textContent).join("");
      else if (v) value = type === "n" || !type ? numText(Number(v.textContent)) : v.textContent;
      place(rows, Number(ref[2]) - 1, col, value);
    }
    return dense(rows);
  }

  // ---- .xls: OLE2 compound file + BIFF8 ------------------------------------------------
  function workbookStream(bytes) {
    const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    if (v.getUint32(0, true) !== 0xe011cfd0) throw new Error("ole2");
    const secSize = 1 << v.getUint16(30, true), miniSize = 1 << v.getUint16(32, true);
    const sector = id => bytes.subarray((id + 1) * secSize, (id + 2) * secSize);
    // DIFAT: 109 entries in the header, then a chain of DIFAT sectors
    const fatSectors = [];
    for (let i = 0; i < 109; i++) fatSectors.push(v.getInt32(76 + i * 4, true));
    for (let d = v.getInt32(68, true), n = v.getUint32(72, true); d >= 0 && n-- > 0;) {
      const s = new DataView(bytes.buffer, bytes.byteOffset + (d + 1) * secSize, secSize);
      for (let i = 0; i < secSize / 4 - 1; i++) fatSectors.push(s.getInt32(i * 4, true));
      d = s.getInt32(secSize - 4, true);
    }
    const fat = [];
    for (const id of fatSectors.filter(id => id >= 0)) {
      const s = new DataView(bytes.buffer, bytes.byteOffset + (id + 1) * secSize, secSize);
      for (let i = 0; i < secSize / 4; i++) fat.push(s.getInt32(i * 4, true));
    }
    const chain = (start, table, read, size) => {
      const parts = [];
      for (let id = start, guard = 0; id >= 0 && guard < 1e6; id = table[id], guard++) parts.push(read(id));
      const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
      parts.reduce((o, p) => { out.set(p, o); return o + p.length; }, 0);
      return size === undefined ? out : out.subarray(0, size);
    };
    const dir = chain(v.getInt32(48, true), fat, sector);
    const dv = new DataView(dir.buffer, dir.byteOffset, dir.byteLength);
    const entries = [];
    for (let o = 0; o + 128 <= dir.length; o += 128) {
      const len = dv.getUint16(o + 64, true);
      const name = String.fromCharCode(...new Uint16Array(dir.slice(o, o + Math.max(0, len - 2)).buffer));
      entries.push({ name, type: dir[o + 66], start: dv.getInt32(o + 116, true), size: dv.getUint32(o + 120, true) });
    }
    const wb = entries.find(e => e.type === 2 && (e.name === "Workbook" || e.name === "Book"));
    if (!wb) throw new Error("workbook");
    if (wb.size >= v.getUint32(56, true)) return chain(wb.start, fat, sector, wb.size);
    // Small streams live in the mini stream (the root entry's data)
    const mini = chain(entries[0].start, fat, sector);
    const minifat = [];
    const mf = chain(v.getInt32(60, true), fat, sector);
    const mfv = new DataView(mf.buffer, mf.byteOffset, mf.byteLength);
    for (let i = 0; i < mf.length / 4; i++) minifat.push(mfv.getInt32(i * 4, true));
    return chain(wb.start, minifat, id => mini.subarray(id * miniSize, (id + 1) * miniSize), wb.size);
  }

  function readXls(bytes) {
    const s = workbookStream(bytes);
    const v = new DataView(s.buffer, s.byteOffset, s.byteLength);
    const records = [];
    for (let p = 0; p + 4 <= s.length;) {
      const type = v.getUint16(p, true), len = v.getUint16(p + 2, true);
      records.push({ type, start: p + 4, data: s.subarray(p + 4, p + 4 + len) });
      p += 4 + len;
    }
    // A string that may run on into CONTINUE records; each continuation starts with a new
    // high-byte flag for the characters (XLUnicodeRichExtendedString)
    function reader(segments) {
      let seg = 0, pos = 0;
      const left = () => segments[seg].length - pos;
      const next = () => { seg++; pos = 0; };
      const byte = () => { if (left() <= 0) next(); return segments[seg][pos++]; };
      const u16 = () => byte() | (byte() << 8);
      const u32 = () => (u16() | (u16() << 16)) >>> 0;
      const skip = n => { while (n > 0) { if (left() <= 0) next(); const k = Math.min(n, left()); pos += k; n -= k; } };
      function string(rich = true) {
        const cch = u16();
        let flags = byte();
        const runs = rich && flags & 8 ? u16() : 0;
        const ext = rich && flags & 4 ? u32() : 0;
        let out = "";
        for (let n = 0; n < cch;) {
          const wide = flags & 1;
          if (left() < (wide ? 2 : 1)) {
            if (seg >= segments.length - 1) break; // a truncated file: keep what was read
            next();
            flags = segments[seg][pos++];
            continue;
          }
          const take = Math.min(cch - n, wide ? left() >> 1 : left());
          for (let i = 0; i < take; i++) out += String.fromCharCode(wide ? u16() : byte());
          n += take;
        }
        skip(runs * 4 + ext);
        return out;
      }
      return { string, u32, done: () => seg >= segments.length - 1 && left() <= 0 };
    }
    let sst = [];
    const sstAt = records.findIndex(r => r.type === 0xfc);
    if (sstAt >= 0) {
      const segments = [records[sstAt].data.subarray(8)];
      for (let i = sstAt + 1; records[i] && records[i].type === 0x3c; i++) segments.push(records[i].data);
      const count = new DataView(records[sstAt].data.buffer, records[sstAt].data.byteOffset).getUint32(4, true);
      const r = reader(segments);
      for (let i = 0; i < count && !r.done(); i++) sst.push(r.string());
    }
    // The first worksheet: BOUNDSHEET gives where its BOF is
    const sheet = records.find(r => r.type === 0x85);
    const from = sheet ? records.findIndex(r => r.start - 4 === new DataView(sheet.data.buffer, sheet.data.byteOffset).getUint32(0, true)) : -1;
    const rk = x => {
      let n;
      if (x & 2) n = x >> 2;
      else {
        const b = new DataView(new ArrayBuffer(8));
        b.setUint32(4, x & 0xfffffffc, true);
        n = b.getFloat64(0, true);
      }
      return x & 1 ? n / 100 : n;
    };
    const rows = [];
    for (let i = Math.max(0, from + 1); i < records.length && records[i].type !== 0x0a; i++) {
      const { type, data } = records[i];
      const d = new DataView(data.buffer, data.byteOffset, data.byteLength);
      const row = data.length >= 4 ? d.getUint16(0, true) : 0, col = data.length >= 4 ? d.getUint16(2, true) : 0;
      if (type === 0xfd) place(rows, row, col, sst[d.getUint32(6, true)] ?? "");
      else if (type === 0x203) place(rows, row, col, numText(d.getFloat64(6, true)));
      else if (type === 0x27e) place(rows, row, col, numText(rk(d.getUint32(6, true))));
      else if (type === 0xbd) {
        for (let k = 0, c = col; 6 + k * 6 + 6 <= data.length - 2; k++, c++) place(rows, row, c, numText(rk(d.getUint32(6 + k * 6 + 2, true))));
      } else if (type === 0x204) place(rows, row, col, reader([data.subarray(6)]).string(false));
      else if (type === 0x06) {
        // FORMULA: a cached number, or a string in the STRING record that follows
        if (d.getUint16(12, true) !== 0xffff) place(rows, row, col, numText(d.getFloat64(6, true)));
        else if (data[6] === 0 && records[i + 1] && records[i + 1].type === 0x207) place(rows, row, col, reader([records[i + 1].data]).string(false));
      }
    }
    return dense(rows);
  }

  // file: a File or Blob with a name. Returns the first sheet as rows of strings.
  window.CLIB.readSheet = async function (file) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    const ext = (/\.(\w+)$/.exec(file.name || "") || [])[1]?.toLowerCase();
    // By content first: a CSV saved as .xls, or an .xls named .xlsx, still reads
    if (bytes[0] === 0xd0 && bytes[1] === 0xcf) return readXls(bytes);
    if (bytes[0] === 0x50 && bytes[1] === 0x4b) return readXlsx(bytes);
    if (ext === "xls" || ext === "xlsx") {
      const text = decodeText(bytes);
      if (!/[\u0000-\u0008]/.test(text.slice(0, 512))) return parseCsv(text);
      throw new Error("엑셀 파일을 읽을 수 없습니다.");
    }
    return parseCsv(decodeText(bytes));
  };
})();
