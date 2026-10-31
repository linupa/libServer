// Code 39 barcode as an SVG string, for member cards (CLIB uses Barcode39.DrawBarcode).
(function () {
  // Nine elements per character, bar/space alternating starting with a bar; 1 = wide
  const PATTERNS = {
    0: "000110100", 1: "100100001", 2: "001100001", 3: "101100000", 4: "000110001",
    5: "100110000", 6: "001110000", 7: "000100101", 8: "100100100", 9: "001100100",
    A: "100001001", B: "001001001", C: "101001000", D: "000011001", E: "100011000",
    F: "001011000", G: "000001101", H: "100001100", I: "001001100", J: "000011100",
    K: "100000011", L: "001000011", M: "101000010", N: "000010011", O: "100010010",
    P: "001010010", Q: "000000111", R: "100000110", S: "001000110", T: "000010110",
    U: "110000001", V: "011000001", W: "111000000", X: "010010001", Y: "110010000",
    Z: "011010000", "-": "010000101", ".": "110000100", " ": "011000100", "*": "010010100",
    $: "010101000", "/": "010100010", "+": "010001010", "%": "000101010",
  };
  const NARROW = 1, WIDE = 2.5;

  window.CLIB = window.CLIB || {};
  window.CLIB.code39 = function (text, height = 30) {
    const chars = `*${String(text).toUpperCase().replace(/[^0-9A-Z\-. $/+%]/g, "")}*`;
    let x = 0;
    const bars = [];
    for (const ch of chars) {
      [...PATTERNS[ch]].forEach((w, i) => {
        const width = w === "1" ? WIDE : NARROW;
        if (i % 2 === 0) bars.push(`<rect x="${x}" width="${width}" height="${height}"/>`);
        x += width;
      });
      x += NARROW; // gap between characters
    }
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${x} ${height}" preserveAspectRatio="none" role="img" aria-label="${text}">${bars.join("")}</svg>`;
  };
})();
