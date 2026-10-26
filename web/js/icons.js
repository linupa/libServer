// Toolbar icons (32x32). Drawn for this port; CLIB's own toolbar bitmaps aren't copied.
(function () {
  const book = (x, y, c, d) => `<rect x="${x}" y="${y}" width="9" height="20" rx="1" fill="${c}" stroke="${d}"/><path d="M${x + 2} ${y + 4}h5M${x + 2} ${y + 15}h5" stroke="#fff" stroke-opacity=".7"/>`;
  const person = (c, d) => `<circle cx="16" cy="10" r="6" fill="#f6c28b" stroke="#c98b4f"/><path d="M5 29c0-7 5-11 11-11s11 4 11 11z" fill="${c}" stroke="${d}"/>`;
  const gearPath = "M16 4l2.2 3.1 3.7-1 .6 3.8 3.6 1.4-1.4 3.6L27 18l-3.1 2.2 1 3.7-3.8.6-1.4 3.6-3.6-1.4L14 29l-2.2-3.1-3.7 1-.6-3.8-3.6-1.4 1.4-3.6L3 15l3.1-2.2-1-3.7 3.8-.6L10.3 4.9l3.6 1.4z";
  const arrow = (d, c) => `<path d="${d}" fill="${c}" stroke="#1d4f91" stroke-linejoin="round"/>`;

  const ICONS = {
    book: book(11, 6, "#3b7dd8", "#1d4f91") + `<path d="M8 27h16" stroke="#7a5a3a" stroke-width="2"/>`,
    books: book(4, 7, "#d9534f", "#9c2f2c") + book(12, 5, "#3b7dd8", "#1d4f91") + book(20, 8, "#5cb85c", "#3a7d3a"),
    lend: book(4, 6, "#3b7dd8", "#1d4f91") + arrow("M15 14h8v-4l7 7-7 7v-4h-8z", "#5cb85c"),
    return: book(19, 6, "#3b7dd8", "#1d4f91") + arrow("M17 14H9v-4l-7 7 7 7v-4h8z", "#f0ad4e"),
    reserve: book(5, 6, "#3b7dd8", "#1d4f91") + `<circle cx="22" cy="21" r="8" fill="#fff" stroke="#8e44ad" stroke-width="2"/><path d="M22 16v5l3 2" stroke="#8e44ad" stroke-width="2" fill="none"/>`,
    list: `<rect x="5" y="4" width="22" height="25" rx="2" fill="#fff" stroke="#5d6b7e"/><path d="M9 10h14M9 15h14M9 20h14M9 25h9" stroke="#3b7dd8" stroke-width="2"/>`,
    overdue: `<circle cx="16" cy="16" r="12" fill="#fff" stroke="#d9534f" stroke-width="2.5"/><path d="M16 9v8l5 3" stroke="#d9534f" stroke-width="2.5" fill="none"/><circle cx="26" cy="6" r="4" fill="#d9534f"/>`,
    rfid: `<rect x="6" y="9" width="14" height="18" rx="2" fill="#5d6b7e" stroke="#2d3746"/><rect x="9" y="12" width="8" height="6" fill="#9fd3ff"/><path d="M22 10a6 6 0 0 1 0 8M25 7a10 10 0 0 1 0 14" stroke="#3b7dd8" stroke-width="2" fill="none"/>`,
    setting: `<rect x="4" y="5" width="24" height="22" rx="2" fill="#fff" stroke="#5d6b7e"/><path d="M8 11h16M8 16h16M8 21h16" stroke="#c3ccd8" stroke-width="2"/><rect x="11" y="8.5" width="4" height="5" fill="#3b7dd8"/><rect x="18" y="13.5" width="4" height="5" fill="#5cb85c"/><rect x="10" y="18.5" width="4" height="5" fill="#f0ad4e"/>`,
    gear: `<path d="${gearPath}" fill="#8a96a8" stroke="#4b5566"/><circle cx="16" cy="16.5" r="4.5" fill="#fff" stroke="#4b5566"/>`,
    load: `<path d="M3 10h9l2 3h15v14H3z" fill="#f0c454" stroke="#b38419"/>` + arrow("M16 4v9h-4l6 7 6-7h-4V4z", "#3b7dd8"),
    save: `<rect x="5" y="5" width="22" height="22" rx="2" fill="#3b7dd8" stroke="#1d4f91"/><rect x="9" y="5" width="13" height="8" fill="#fff"/><rect x="9" y="17" width="14" height="10" fill="#e8eef7"/><rect x="18" y="6.5" width="3" height="5" fill="#1d4f91"/>`,
    search: `<circle cx="13" cy="13" r="8" fill="#dff0ff" stroke="#1d4f91" stroke-width="2.5"/><path d="M19 19l8 8" stroke="#7a5a3a" stroke-width="4" stroke-linecap="round"/>`,
    overlap: `<rect x="4" y="4" width="16" height="18" rx="2" fill="#fff" stroke="#5d6b7e"/><rect x="11" y="10" width="16" height="18" rx="2" fill="#fde7c4" stroke="#c98b4f"/><path d="M15 19l3 3 6-7" stroke="#d9534f" stroke-width="2.5" fill="none"/>`,
    check: `<rect x="5" y="4" width="22" height="25" rx="2" fill="#fff" stroke="#5d6b7e"/><path d="M9 11l2 2 4-4M9 19l2 2 4-4" stroke="#5cb85c" stroke-width="2" fill="none"/><path d="M18 11h6M18 19h6" stroke="#5d6b7e" stroke-width="2"/>`,
    edit: `<rect x="4" y="6" width="18" height="22" rx="2" fill="#fff" stroke="#5d6b7e"/><path d="M8 12h10M8 17h10M8 22h6" stroke="#c3ccd8" stroke-width="2"/><path d="M26 6l3 3-12 12-4 1 1-4z" fill="#f0ad4e" stroke="#a4590c"/>`,
    shelf: `<rect x="3" y="4" width="26" height="25" fill="#c8a27a" stroke="#7a5a3a"/><rect x="5" y="6" width="22" height="9" fill="#f3e6d6"/><rect x="5" y="18" width="22" height="9" fill="#f3e6d6"/><path d="M7 7v8M10 8v7M13 7v8M18 7v8M8 19v8M12 20v7M15 19v8M20 19v8M23 20v7" stroke="#3b7dd8" stroke-width="2"/>`,
    barcode: `<rect x="3" y="6" width="26" height="20" rx="2" fill="#fff" stroke="#5d6b7e"/><path d="M7 9v14M9 9v14M12 9v14M15 9v14M16.5 9v14M19 9v14M22 9v14M23.5 9v14M25 9v14" stroke="#1b2430" stroke-width="1.3"/>`,
    label: `<path d="M4 8h16l8 8-8 8H4z" fill="#fde7c4" stroke="#c98b4f"/><circle cx="9" cy="16" r="2" fill="#c98b4f"/><path d="M13 13h6M13 19h5" stroke="#7a5a3a" stroke-width="1.5"/>`,
    user: person("#3b7dd8", "#1d4f91"),
    users: `<g transform="translate(-5 2) scale(.8)">${person("#5cb85c", "#3a7d3a")}</g><g transform="translate(9 2) scale(.8)">${person("#f0ad4e", "#a4590c")}</g>` + `<g transform="translate(2 4) scale(.85)">${person("#3b7dd8", "#1d4f91")}</g>`,
    card: `<rect x="3" y="7" width="26" height="18" rx="2.5" fill="#e8f1fc" stroke="#1d4f91"/><circle cx="10" cy="14" r="3" fill="#f6c28b"/><path d="M6 21c0-3 2-4 4-4s4 1 4 4z" fill="#3b7dd8"/><path d="M17 12h8M17 16h8M17 20h5" stroke="#5d6b7e" stroke-width="1.5"/>`,
    usersearch: `<g transform="translate(-3 0) scale(.85)">${person("#3b7dd8", "#1d4f91")}</g><circle cx="22" cy="20" r="5" fill="#fff" stroke="#1d4f91" stroke-width="2"/><path d="M25.5 23.5l4 4" stroke="#7a5a3a" stroke-width="3" stroke-linecap="round"/>`,
    idcode: `<rect x="3" y="7" width="26" height="18" rx="2.5" fill="#fff" stroke="#5d6b7e"/><text x="16" y="21" font-size="10" font-family="Arial" font-weight="700" text-anchor="middle" fill="#3b7dd8">A001</text>`,
    userdelete: `<g transform="translate(-3 0) scale(.85)">${person("#8a96a8", "#4b5566")}</g><circle cx="23" cy="21" r="6" fill="#d9534f"/><path d="M20 18l6 6M26 18l-6 6" stroke="#fff" stroke-width="2"/>`,
    bankbook: `<rect x="5" y="4" width="20" height="25" rx="2" fill="#5cb85c" stroke="#3a7d3a"/><rect x="9" y="8" width="12" height="7" fill="#fff"/><path d="M25 8h2v21H9v-2" fill="none" stroke="#3a7d3a"/>`,
    print: `<rect x="9" y="4" width="14" height="9" fill="#fff" stroke="#5d6b7e"/><rect x="3" y="12" width="26" height="11" rx="2" fill="#8a96a8" stroke="#4b5566"/><rect x="9" y="19" width="14" height="10" fill="#fff" stroke="#5d6b7e"/><path d="M12 23h8M12 26h6" stroke="#3b7dd8"/>`,
    chart: `<path d="M4 28h25" stroke="#4b5566" stroke-width="1.5"/><rect x="6" y="18" width="5" height="10" fill="#d9534f"/><rect x="13" y="12" width="5" height="16" fill="#f0ad4e"/><rect x="20" y="6" width="5" height="22" fill="#5cb85c"/>`,
    backup: `<ellipse cx="16" cy="8" rx="11" ry="4" fill="#9fd3ff" stroke="#1d4f91"/><path d="M5 8v15c0 2.2 4.9 4 11 4s11-1.8 11-4V8" fill="#dff0ff" stroke="#1d4f91"/>` + arrow("M16 12v8h-3l3 5 3-5h-3", "#5cb85c"),
    restore: `<ellipse cx="16" cy="8" rx="11" ry="4" fill="#9fd3ff" stroke="#1d4f91"/><path d="M5 8v15c0 2.2 4.9 4 11 4s11-1.8 11-4V8" fill="#dff0ff" stroke="#1d4f91"/>` + arrow("M16 25v-8h-3l3-5 3 5h-3", "#f0ad4e"),
    // 클라우드 다운로드: a cloud with an arrow coming down
    cloud: `<path d="M9 22a6 6 0 0 1-.6-12 8 8 0 0 1 15.3 2.2A5 5 0 0 1 23 22z" fill="#dff0ff" stroke="#1d4f91"/>` + arrow("M16 13v8h-3l3 5 3-5h-3", "#5cb85c"),
    cloudUp: `<path d="M9 22a6 6 0 0 1-.6-12 8 8 0 0 1 15.3 2.2A5 5 0 0 1 23 22z" fill="#dff0ff" stroke="#1d4f91"/>` + arrow("M16 27v-8h-3l3-5 3 5h-3", "#f0ad4e"),
    clock: `<circle cx="16" cy="16" r="12" fill="#fff" stroke="#3b7dd8" stroke-width="2.5"/><path d="M16 8v8l6 3" stroke="#1b2430" stroke-width="2.2" fill="none"/>`,
    board: `<rect x="3" y="5" width="26" height="19" rx="2" fill="#3a7d3a" stroke="#7a5a3a" stroke-width="2"/><path d="M8 11h12M8 15h16M8 19h9" stroke="#fff" stroke-opacity=".85" stroke-width="1.5"/><path d="M10 24l-3 5M22 24l3 5" stroke="#7a5a3a" stroke-width="2"/>`,
  };

  window.CLIB_ICON = name =>
    `<svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true" stroke-width="1">${ICONS[name] || ICONS.list}</svg>`;
})();
