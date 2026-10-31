# CLIB Web

A web frontend for porting CLIB (a small-library management program) away from WinForms.
It copies CLIB's main window: the blue menu tab strip, the icon toolbar with ▾ dropdowns,
and the grey workspace. Screens CLIB docks into the workspace (대출, 도서관리, 회원관리, the
statistics screens…) open there; the rest open as movable modal dialogs at CLIB's window sizes.
It has every table from CLIB, 62 tables on 43 screens. There's no backend yet, so each table
shows deterministic sample data, and toolbar items that aren't ported show a message box.

These screens are working ports of CLIB's forms, laid out from its designer code and run
against an in-memory sample library (it resets on reload). Clicking a top tab opens its
first page (대출/반납 → 대출, 도서관리 → 도서관리, …); 도서관리 and 회원관리 are
opened by their tabs only, without a toolbar button of their own. CLIB's 독서통장 tab and 환경설정's
독서통장 설정 tab are left out, as the library doesn't use them.

- 대출 (`#/lent/BookLent`): member number + Enter, then barcode + Enter (or 대출).
  대출연장 renews; books with 딸림자료 ask whether to lend them too.
- 반납 (`#/lent/BookReturn`): barcode + Enter; the borrower is found from the loan.
  Overdue books are charged 100원 a day, and a book with a waiting reservation is held.
- 예약 (`#/lent/BookReserve`): member number, then the barcode of a book on loan.
  예약취소 cancels. Up to 3 members can wait for one book.
- 도서관리 (`#/book/BookManage`): a work list of books plus the record editor. Load books
  with the pink 저장된 도서 불러오기 box or 불러오기 > 저장된 도서불러오기, edit, then 저장.
  The pink box takes several 등록번호, one per line (Enter adds a line, Ctrl+Enter or
  불러오기 loads them); those not found stay in the box.
  Rows are white when saved, bisque when a required (★) field is missing and grey when
  not saved. 저자기호 생성 follows CLIB's 이재철 5표 (`web/js/authorCode.js`).
  고정필드 shows the MARC fixed fields and 전문가용 shows the record as MARC (F5 ▼, F6 ▲, F7 ↔).
- 도서 불러오기 (`SearchMarc`): 일반검색 by any 검색기준, or 구간검색 by barcode range.
  불러오기 loads the checked books; 전체 불러오기 (in place of CLIB's 전체선택) loads every result.
- 파일로 저장: Marc 파일 저장 (`CRLFDlg`, 일반 or 줄바꿈 문자 포함) saves the books checked in
  도서관리 as one MARC file; 엑셀파일 저장 (`SaveFileProcess`) saves their fields (CLIB's 20
  columns) as CSV. Saved books are unchecked, as in CLIB.
- 연체관리 (`BookDelay`): 연체회원, 연체도서, or 연체회원 with 연체도서 같이 보기 (each member's
  overdue books). With 연체금 납부 the 연체금 / 미납금 / 총 연체금 columns show what is owed.
  CLIB ignores the 검색어 in the 연체도서 같이 보기 list; here it filters by member there too.
- 회원관리 (`#/user/Users`): member editor with 신규 (numbers by grade), 저장 and 삭제, a
  member list filled from 회원검색, and a card preview with photo and Code 39 barcode. With
  연체금 납부 it shows the member's 연체금 and 연체금 완납. The buttons over the list are laid
  out like 도서관리's (전체선택 / 파일로 저장 on the left, 화면지우기 / 일괄삭제 on the right).
- 회원일괄입력 (`BatchInput`): members from an .xls, .xlsx or .csv laid out like CLIB's
  template (샘플파일보기 downloads it). Rows that can't be saved stay listed with the reason;
  중복된 / 삭제된 번호 입력 enter those numbers anyway. `web/js/sheet.js` reads the files
  (CLIB uses Excel itself).
- 이용내역 조회 (`UserLentStats`): the member's 대출 / 반납 / 연체 history, by period and kind.
- 가입신청서 출력 (`JoinPrint`): CLIB's 회원가입 신청서 / 개인정보 동의서 form
  (`web/img/join.jpg`, from CLIB's Sample folder) with the library's name, N copies.
- 회원검색 (`UserSearch`): search by any 검색구분 and load the checked members, or all of them
  with 전체 불러오기 (in place of CLIB's 전체선택), into the screen that opened it (회원관리,
  대출, 반납, 예약).
- 일괄수정 > 회원상태 수정 / 회원등급 수정 (`UserBatchState`, `UserBatchLevel`): sets the state
  or grade of every member checked in 회원관리 and reports 성공 / 실패.
- 등급별 회원번호관리 (`UserCodeDlg`): a grade's members; numbers without the grade's 구분기호 are
  Bisque when numbering by grade. 번호변경 / 전체 재설정 give them the grade's next number.
- 삭제한 회원번호관리 (`DeleteUsers`): deleted members with their history; 삭제 clears the number
  and its history for good, 삭제취소 restores the member (one at a time or 일괄).
- 회원증출력: the card-type chooser, then 회원증 출력, which prints the members checked in
  회원관리 (front and back, card slot 1-4, margins and outline from CLIB's settings).
- 대출/반납 통계 (`#/stats/Lent_ReturnStats`): every combination of 조회기간, 조회기준,
  통계구분 and 표시형태, computed from the lending history; 파일저장 saves CSV, 출력 prints.
- 이용현황 (`#/lent/LentStats`): current loans (overdue rows tinted), reservations, or
  attachments still out, filtered by book or member.
- 데이터베이스 관리 (server only): 데이터백업 saves the database as a SQL Server .bak on the
  server PC (자동백업설정's 백업위치, C:\CLIB\Backup by default) and downloads a copy;
  데이터복구 restores one of those, or a .bak sent from this computer, after backing up the
  current data; 자동백업설정 sets CLIB's automatic backups. The files are the same kind CLIB
  makes, so CLIB's DataRestore.exe and the web can restore each other's backups.
- Settings: 대출환경설정, 회원등급설정, 도서관리설정 on their toolbars, and 환경설정
  with all of them as tabs plus 도서관 설정. Saving changes how the other screens work:
  loan periods and limits per grade, renewals (연장불가 / 대출일 비례 / 일괄적용), overdue rules
  (대출정지 or 연체금), reservations, re-lending confirmation and the same-book ban, member
  numbering by grade, the 저자기호 table and options, and the holding locations.

The toolbars match CLIB without an RFID reader, so RFID태깅 and 대출반납확인 are hidden.

Sample data:

- settings as in this install's 환경설정 screenshots: grades Child (AA), Adult (AB), Admin
  (AD) and Premium (PR) with 21 days, 5 loans and 3 reservations; renewals 대출일 비례 x1 up
  to 10 times; reservations held 3 days with up to 3 waiting; locations 서가, 작가별, 참고
- member numbers AA0001-AA0010 (Child), AB0001-AB0015 (Adult), AD0001-AD0002 (Admin),
  PR0001-PR0003 (Premium); AB0003 is 대출중지; AB0016 and AA0011 are deleted members
- book barcodes EM000001-EM000120; every 15th has 딸림자료, EM000010 is held for AA0004,
  and a few are 분실 or 파손
- codes (도서상태, 반입구분, 회원상태) follow CLIB's `DATA/CODE_SUB.csv`
- about four months of lending history for the statistics; lending and returning add to it
- library details (HKMCC) and the card notice, as in the screenshots

URLs follow `#/<tab>/<docked view>/<dialog>/<nested dialog>`, for example
`#/book/BookManage/SearchMarc` or `#/lent/-/LentOption/RestDateDlg` (`-` = no view).

## Run

Open `web/index.html` in a browser to use the sample data; there's no build step.

To use CLIB's real database, run `server\run.bat` on Windows and open
<http://127.0.0.1:8080/>. See [server/README.md](server/README.md). Every ported form reads
the real data. 대출, 반납, 대출연장, 예약, 예약취소, saving or deleting members and books, and
the settings screens write to it the way CLIB does. The table-only preview screens still show sample rows, and the
status bar shows which data each screen is using.

## Layout

```
tools/extract_tables.py   pulls table definitions out of decompiled CLIB source
tools/extract_forms.py    pulls form layouts (controls and positions) out of it
tools/extract_author_tables.py  converts CLIB's Code/*.csv author tables
web/index.html            app shell
web/css/app.css           styles (classic Windows look)
web/js/tables.js          GENERATED: screens, tables, columns, window sizes
web/js/menus.js           tab strip, toolbar items, and which dialogs each screen opens
web/js/icons.js           toolbar icons (drawn for this port, not CLIB's bitmaps)
web/js/forms.js           GENERATED: control layouts of ported forms
web/js/data.js            data provider (sample rows) and the sample library
web/js/api.js             the same library backed by the server, when served by it
server/                   local server over CLIB's database (Windows)
web/js/authorTables.js    GENERATED: 동양서, 이재철 1-8표, 장일세, Cutter-Sanborn tables
web/js/authorCode.js      저자기호, ported from CLIB (all tables and options)
web/js/code39.js          Code 39 barcodes for member cards
web/js/sheet.js           reads .xls / .xlsx / .csv files (회원일괄입력)
web/img, web/sample       CLIB's 가입신청서 form image and 회원일괄입력 template (from its Sample folder)
web/js/screens/*.js       behaviour of ported forms (circulation.js is shared by 대출/반납/예약)
web/js/app.js             shell, dialogs, and the table component
```

## Table definitions

`web/js/tables.js` is generated from the decompiled CLIB source (ILSpy output):

```
python3 tools/extract_tables.py <path to CLIB_decompiled>
```

The script reads every `DataGridView` and `ListView` in the decompiled forms and records
each table's column headers, column types (text, checkbox, button, image), widths and
hidden columns. Each column also gets an English `key`, such as `barcode`, `title` or
`userId`, from the `HEADER_KEYS` table in the script. Rows are objects keyed this way.

It also records each form's `ClientSize`, which sets the dialog sizes. The script's
`SCREENS` and `TABLE_LABELS` tables set each screen's display title and the labels on
screens with more than one table. They also list the tables that are skipped:

- `BookOption.dataGridView2` (hidden in CLIB)
- `SearchBooks.tmp_list` (a hidden scratch list)
- `BookListPrint.dgGrid` (a print copy of another grid)

`web/js/menus.js` is hand-written from CLIB's `TopMenu/*.cs` and `BookDream.Select*Menu()`.
It decides which toolbar item opens which docked view or dialog, and which buttons a screen
shows for its sub-dialogs (from the `new XxxDlg(` callers in the decompiled code).

Hidden columns, such as CLIB's DB keys (`seq`, `rowKey`, `marc`), stay in the definitions
but aren't displayed.

## Form layouts

`web/js/forms.js` is generated the same way:

```
python3 tools/extract_forms.py <path to CLIB_decompiled>
```

It reads a form's `InitializeComponent()` and records every label, text box, combo box
(with its items), radio button, button, group box, tab control and list with its `Location`,
`Size`, text, colours, alignment, and read-only/bold/hidden flags. The forms to extract,
and the controls to leave out, are listed in `FORMS` at the top of the script. It leaves
out the banner images (vendor adverts) and the RFID-only buttons, which CLIB hides when
no reader is connected.

`web/js/authorTables.js` comes from the CLIB install itself:

```
python3 tools/extract_author_tables.py "/mnt/c/Program Files (x86)/CLIB/CLIB Free"
```

A form is drawn from its layout when a `CLIB_LOGIC` entry exists for it. The entry's
`layout` (a left/right panel split) or `arrange` function says how the top-level controls
stretch, following the form's `SizeChanged` handler; `columns` gives the list column
divisors from `List_SizeChanged()`; `init(ctx)` wires up the controls.

## Adding a backend

Replace `getRows()` in `web/js/data.js`:

```js
getRows(screen, table) {
  return fetch(`/api/${screen.id}/${table.id}`).then(r => r.json());
}
```

Return an array of objects that use the column keys from `tables.js`, and set
`isSample: false` to hide the "샘플 데이터" (sample data) badge.

Button columns (보안설정, 삭제, 번호변경, …) currently only show a message box.

The ported screens use `window.CLIB.library` in `data.js` instead: `findUser`,
`findUsersByName`, `findBook`, `allBooks`, `searchBooks`, `lend`, `extend`, `returnBook`,
`reserve`, `cancelReserve`, `saveBook`, `deleteBook`, `searchUsers`, `nextUserId`,
`saveUser`, `deleteUser`, `history`, `allLoans`, `allReservations`, `overdue`, `marcFile`,
`usersByGrade`, `renumberUser`, `deletedUsers`, `purgeUser`, `restoreUser`, `payCharge` and
`userHistory`, plus `settings`
(everything the settings screens edit) and `saveSettings`. A backend version should keep the
same return shapes: `{ error }`, `{ confirm, title }` (ask, then call again with the
answer) or `{ ok, ... }`.
