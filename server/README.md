# CLIB Web server

A small local server that serves the web app (`../web`) and a JSON API over CLIB's own
database. It reads everything the ported screens show, and writes lending, returns,
renewals, reservations, members, books and settings the way CLIB does.

## Why it runs on Windows

CLIB Free keeps its data in a SQL Server LocalDB file, `C:\CLIB\Data\CLIB.mdf`, opened
through `(localdb)\v11.0`. LocalDB only accepts local Windows connections, so the server
runs under Windows Python. It isn't reachable from WSL or from other PCs; it binds to
`127.0.0.1` because there is no login yet.

## Run

```
server\run.bat
```

The first run creates `.venv` and installs `requirements.txt` (Flask, pyodbc). The one
server process listens on two ports, each serving its own web app over the same `/api`:

| Port | Web app | Folder | Replaces |
|---|---|---|---|
| <http://127.0.0.1:8080/> | the library's app | `web/` | CLIB.exe |
| <http://127.0.0.1:8081/> | the self-service kiosk (not ported yet) | `web-self/` | CLIB_Self.exe |

Writes from both go through the same lock, so a kiosk loan and a desk return can't collide.

### Starting and stopping

As it starts, the server backs up the database (CLIB's `yyyyMMdd_ON.bak` safety copy, and
자동백업 when due) and then downloads it from the cloud; the page shows a banner until that is
done. The 종료 tab backs up (`_OFF.bak`), uploads to the cloud and then stops the server. A
failed backup stops either sequence before anything is replaced or sent, and a failed upload
leaves the server running so 종료 can be tried again. Stopping the server with Ctrl+C only backs up.
The server refuses to start if either port is already taken (Windows would otherwise let a
second copy bind the same port). Opening `web/index.html` straight from disk still works and
uses the sample data.

## Database

The server works on CLIB's own database, `C:\CLIB\Data\CLIB.mdf`, under the name `CLIB`
that CLIB and CLIB_Self use, so all three share one set of data: a loan at the web desk or
kiosk is a loan in CLIB, and a cloud download replaces CLIB's data. Back it up before trying
anything risky (CLIB's own backup, or copy `CLIB.mdf` and `CLIB_log.ldf` with LocalDB stopped).

CLIB numbers new rows MAX(SEQ)+1 without locking. The server locks while it numbers, but
CLIB doesn't, so the same history number could be taken twice if CLIB and the web write at
the very same moment; working at one of them at a time avoids it.

To work on a copy instead, create `config.json` (not in git):

```json
{ "dbPath": "C:\\CLIB\\WebData\\CLIB.mdf", "dbName": "CLIB_WEB" }
```

The copy needs a name of its own: LocalDB can't attach two files as `CLIB`. `CLIB_DB` (an
environment variable) overrides the path as well.

To refuse all writes, add `"readOnly": true` to `config.json`.

When LocalDB has had a database attached it changes the files' permissions, so WSL can't
overwrite them. Stop the server and LocalDB (`sqllocaldb stop v11.0`) and copy from
Windows (`copy /Y` in cmd or Explorer) instead.

## Layout

```
app.py               Flask app: static files and the /api routes
db.py                connection (ODBC Driver 17, LocalDB, UTF-16 for Korean text)
repo.py              queries; returns the same shapes as the sample library in web/js/data.js
circulation.py       lending, returns, renewals, reservations and CLIB's daily checks (writes)
records.py           saving and deleting members and books, and the books' MARC records (writes)
settings_store.py    saving settings (writes; CLIB.exe.Config values go to clib_settings.json)
backup.py            데이터백업 / 데이터복구 / 자동백업설정 (BACKUP and RESTORE DATABASE)
tools/dump_schema.py writes schema.md (tables, columns, row counts; no member or book rows)
schema.md            the database layout
run.bat              start script
```

## API

| route | returns |
|---|---|
| `GET /api/meta` | database path, today, and all settings: USER_LEVEL, LENT_OPTION, CODE_SUB, LIBRARY (card text), BANKBOOK_OPTION, REST_WEEK, 별치기호 values, and a few CLIB.exe.Config keys |
| `GET /api/users/<id>` | member with loans and reservations (404 if none) |
| `GET /api/users/<id>/history` | 이용내역 조회: `{userId, userName, rows}` with each RENTAL_HISTORY row's date, book and 대출/반납/연체/예약 |
| `GET /api/users/<id>/photo` | the member's photo file (USER_IMAGE), only from the photo folders (see below) |
| `POST /api/users/<id>/photo` | save a photo (the image is the body) as `<회원번호>.<ext>` in `photoDir` and point USER_IMAGE at it |
| `GET /api/users/next?grade=` | the next member number (by grade or one sequence, per 회원등급설정) |
| `GET /api/users?name=` | members with that exact name |
| `GET /api/users?field=&q=` | 회원검색: field is 회원번호, 회원명, 회원등급, 회원상태, 주소, 전화번호, 이메일 |
| `GET /api/users?grade=` | 등급별 회원번호관리: every member of one grade `[{userGrade, userId, userName}]` |
| `GET /api/users/deleted` | 삭제한 회원번호관리: deleted members with their 대출 / 반납 / 연체 counts up to the deletion, and the deletion time (MOD_DATE) |
| `GET /api/overdue` | 연체관리: `{users, loans}`, the 연체중 members (with their overdue count and unpaid 연체금) and every overdue loan with its borrower |
| `GET /api/books/<barcode>` | book with its loan and waiting list (404 if none); `?full=1` adds the MARC fields and MARC text |
| `GET /api/books?field=&q=` / `?start=&end=` | 도서 불러오기 searches (up to 1000) |
| `GET /api/stats/books?by=` | 도서보유현황 totals: by 0 도서상태 (BOOK_LENT rows), 1 도서분류, 2 별치기호, 3 소장위치, 4 반입구분; `[{name, count}]`, 전체 first |
| `GET /api/stats/books/detail?by=&name=&row=` | the books of one row (도서분류 by `row`, the others by `name`; 전체 = all) |
| `GET /api/stats/users?by=` | 이용자현황 totals: by 0 회원등급, 1 회원상태 |
| `GET /api/stats/users/detail?by=&name=` | the members of one row, with their 대출 and 연체 counts from RENTAL_HISTORY |
| `GET /api/search?field=&q=` | the kiosk's 도서검색 (전체/서명/저자/출판사/등록번호/총서명/발행년도, spaces ignored; no field = every book). Book details only, nothing about borrowers |
| `GET /api/loans` | every current loan (이용현황) |
| `GET /api/reservations` | every reservation with its place in the queue |
| `GET /api/history?from=&to=` | RENTAL_HISTORY between two dates (대출/반납 통계) |
| `POST /api/lend` `{userId, barcode, answers}` | lend a book. `answers.preview`: run every check and return `{preview}` (due date etc.) without writing |
| `POST /api/return` `{barcode, answers}` | return a book (the borrower comes from the loan). `answers.preview` as for lend; `answers.kiosk`: refuse books someone has reserved (they go back at the desk) |
| `POST /api/extend` `{barcode}` | renew a loan |
| `POST /api/reserve` `{userId, barcode}` | reserve a book that is out |
| `POST /api/reserve/cancel` `{userId, barcode}` | cancel a reservation |
| `POST /api/users` `{user, answers}` | save a member (`user.isNew` when 신규) |
| `POST /api/users/delete` `{userId}` | delete a member |
| `POST /api/books` `{book, original, answers}` | save a book (`original` = its barcode when opened, null for new) |
| `POST /api/books/delete` `{barcode}` | delete a book |
| `POST /api/books/marcfile` `{items, crlf}` | Marc 파일 저장: `items` = `[{original, record}]`; returns the MARC file (CP949), the record count in `X-Record-Count`. Reads only |
| `POST /api/users/paycharge` `{userId}` | 연체금 완납 |
| `POST /api/users/renumber` `{userId, grade, answers}` | 번호변경: asks (`answers.renumber`), then gives the member the grade's next number |
| `POST /api/users/purge` `{userId, deleteDate}` | 삭제한 회원번호 삭제: the deleted member and its history up to `deleteDate` |
| `POST /api/users/restore` `{userId}` | 삭제취소: bring a deleted member back |
| `POST /api/settings` `{changes}` | save settings; answers `{ ok, settings }` with everything re-read |
| `GET /api/backup` | backup files in both folders, the 자동백업설정 options and the folders |
| `POST /api/backup` | 데이터백업: a new `yyyyMMdd_HHmmss.bak` (reads only, so allowed when read-only) |
| `GET /api/backup/file?folder=&name=` | download a backup (`folder`: `backup` or `auto`) |
| `POST /api/backup/upload?name=` | a .bak in the request body, kept in the backup folder as `upload_…` |
| `POST /api/backup/restore` `{folder, name}` | 데이터복구 (refused when read-only) |
| `POST /api/backup/options` `{auto, path, days, run}` | 자동백업설정; turning it on backs up at once, as in CLIB |

The POST routes answer `{ error }`, `{ confirm, title, ask }` or `{ ok, ... }`. A question
(재대출, 딸림자료, a missing borrower) is asked before anything is written; send the same
request again with `answers[ask]` set to true or false.

LIBRARY.PASSWORD is never read. From CLIB.exe.Config only these keys are read: AUTHORCODE,
AUTHOR, BOOK, MOUM, TOTAL, PUBLISH, ISBN_SEARCH, USERCODE, CARD_* and CLAIM_* (never DBCONN). Set
`clibDir` in `config.json` if CLIB is installed somewhere else. Searches return at most 1000 rows.

Member photos: USER_IMAGE holds the full path CLIB saved a photo to (its `UserImage` folder).
When that file isn't there, a file of the same name is looked for in CLIB's `UserImage`, the
copy Windows keeps of it under `%LOCALAPPDATA%\VirtualStore` (CLIB isn't allowed to write to
Program Files), and `photoDir`, so photos copied over from another PC show once they are put
in one of those. Photos chosen on the web are saved in `photoDir` (`C:\CLIB\UserImage` by
default; the server can't write under Program Files), and CLIB reads them from the path it
finds in USER_IMAGE. JPG, PNG, GIF and BMP up to 10 MB.

## How the codes map

- `CODE_SUB`: 000 회원등급, 001 도서상태, 002 소장위치, 003 회원상태, 004 반입구분
- `BOOK_LENT.STATS`: 1 대출중, 3 연체중 (a loan is either); 0 대출가능, 4 분실, …
- `RENTAL_HISTORY.BOOK_STATE`: 1 대출, 0 반납, 3 연체
- `BOOK` and `BOOK_LENT` join on `SEQ`; dates are text such as `2026-08-02 12:21:31`
- `BOOK.ATTACH` is a Y/N flag; the attachment's description is in the MARC record
- `MARC.MARC_DATA` is ISO 2709 (joined to BOOK on SEQ). Its directory lengths count CP949
  bytes, so fields are split on the field terminator. 도서관리 reads 260 ▼a/▼b/▼c (발행지,
  출판사, 출판년도), 300 ▼a/▼c/▼e (페이지, 크기, 딸림자료) and 950 ▼b (가격), as CLIB's
  AnalysisMarc does
- `LIBRARY.NOTICE` is the card back: title, notice and library name separated by tabs

## Lending, returns, renewals and reservations

`circulation.py` ports CLIB's `BookLent.LentBook()`, `BookReturn.ReturnBook()`,
`ExtendBook()`, `BookReserve.ReserveBook()` and its 예약취소, with parameters instead of string-built SQL. Each request runs alone (a
lock) in one transaction that commits only when it succeeds. History rows are numbered
`MAX(SEQ)+1` as in CLIB, read under an update lock.

- **Lend:** short barcodes are padded as in CLIB (HK915 → HK00000915); the book must be
  대출가능 or held for this member; 반납 후 대출 금지; loan limit; 연체중 members only when
  연체중에도 대출가능; 대출중지 members never; 재대출 and 딸림자료 questions. The due date is
  the grade's loan days (one fewer with 대출일 포함하기), moved past REST_WEEK days,
  REST_DATE dates and PUBLIC_RESTDATE holidays. Writes BOOK_LENT (STATS 1, the next
  waiting member in RESERVE_USER), RENTAL_HISTORY (1) and, with the 딸림자료,
  BOOK_LENT.ATTACH and ATTACH_HISTORY (0).
- **Return:** an overdue return applies 연체규정 (대출정지 until a date, or a 연체금 up to
  the maximum) to USERS, as CLIB computes it; then BOOK_LENT goes back to 대출가능, or 예약중
  when someone is waiting; RENTAL_HISTORY (0); the 딸림자료 back with ATTACH_HISTORY (1).
- **Renew:** refused for reserved or overdue books and at the 연장 limit; the new due date
  follows 대출일 비례 / 일괄적용 and the closing days.
- **Reserve:** reservations must be on (예약규정); only books that are out (대출중, 연체중,
  예약중); the queue limit (RESERVE_MAX); not the borrower; the member's grade limit and
  정상 status; not twice. Writes RESERVATION, a RENTAL_HISTORY row (2), and makes the member
  BOOK_LENT.RESERVE_USER when nobody is first yet. The first member waiting is who a
  returned book is held for (STATS 2) and who may borrow it; lending it to them removes
  their reservation and moves RESERVE_USER to the next one.
- **Cancel:** deletes the RESERVATION row and moves RESERVE_USER to the next member; a held
  book with nobody left waiting becomes 대출가능 again.
- **Daily checks:** once a day, before the first API request, the server does what CLIB's
  start page does: marks loans past their due date 연체중 (and the member, with a history
  row the first time), passes held books on to the next member after the hold days, and
  ends suspensions that have run out.

Differences from CLIB:

- CLIB's same-book ban compares the dates the wrong way round, which would block for good;
  this follows its message ("… 까지").
- `BOOK.ATTACH` is the attachment's description and 'N' means none; CLIB would ask about
  an attachment called "N".
- 재대출 (확인 후 대출) counts only past loans. CLIB counts every history row, so a member
  collecting a book they had reserved was asked "해당 회원이 대출했던 도서입니다".
- Cancelling the last reservation of a held book also clears RESERVE_DATE (CLIB leaves it).
- Saving an existing member doesn't ask "동일한 회원번호가 이미 존재합니다" every time, only
  when 신규 would overwrite someone. With one shared number sequence CLIB also narrows an
  all-digit number by the grade prefix's length; that isn't copied.
- Members with a reading passbook (BANKBOOK_USER) aren't lent to yet, because CLIB also
  writes BANKBOOK_HISTORY for them; there are none in the current database.

## Members and books

`records.py` ports `Users.SaveUsers()` / `DeleteUsers()` and `BookManage.SaveMarcDB()` /
`DeleteMarcDB()`.

- **Member numbers (신규):** `Users.NewUser()`. Numbering by grade gives the grade's 구분기호
  plus the next number at the same width; one shared sequence continues the highest member
  number, keeping its letters (AB0634 → AB0635).
- **Save member:** 회원번호 letters and digits only, 회원명 required, grade must exist. A number
  left by a deleted member can be reused after a question, which removes the old member and
  its history (as CLIB does). A new member's number already in use asks before overwriting.
  New members get SEQ = MAX+1 and REG_DATE in CLIB's "yyyy-MM-dd, HH:mm:ss"; back to 정상
  clears the suspension date. The 연체금 amount is kept as stored (this install hides it).
- **Delete member:** refused with books, reservations or attachments out; otherwise
  DELETE_YN='Y', and the member leaves any waiting list.
- **Save book:** the ★ fields; 소장위치/반입구분/도서상태 by name from CODE_SUB; a barcode
  already in use asks before overwriting; changing a saved book's 등록번호 asks, refuses one
  in use, and moves BOOK, BOOK_LENT, RENTAL_HISTORY, ATTACH_HISTORY, RESERVATION and
  BARCODE_UID to the new number. A barcode left by a deleted book is cleared first (its old
  rows and history), as CLIB does. A book on loan or reserved can't be given another status.
  Writes BOOK (with CLIB's CLAIM string `별치_분류_저자기호_권차_복본`), BOOK_LENT.STATS and
  BARCODE_UID for an RFID.
- **MARC:** each book's record is updated the way CLIB's form edits it (ModifyExpertEdit):
  only the fields whose value changed are written to their subfields (020 ▼a/▼c, 049
  ▼l/▼v/▼c/▼f, 056 ▼a, 090 ▼a/▼b/▼c, 100 ▼a, 245 ▼a/▼n/▼d, 260 ▼a/▼b/▼c, 300 ▼a/▼c/▼e,
  440 ▼a/▼v, 950 ▼b), everything else is kept, 005 gets the save time, and the record is
  rebuilt as CreateMarc() does with CP949 byte lengths. A new book starts from NewMarc()'s
  template. Rebuilding every stored record unchanged gives back exactly the same bytes.
  Edits typed into the 전문가용 tab aren't saved yet.
- **Delete book:** refused while out or reserved; BOOK, BOOK_LENT and MARC get DELETE_YN='Y'.
- **회원일괄입력:** each row goes through the same save as 회원관리's 신규 (so a number in use
  or left by a deleted member asks first; the screen answers no and lists the row, and
  중복된 / 삭제된 번호 입력 answer yes).
- **연체금 완납:** `Users.btn_charge_Click()`. DELAY_CHARGE 0, and the member is 연체중 while a
  book is still overdue, otherwise 정상 (clearing the suspension date).
- **이용내역 조회:** `UserLentStats.LoadUserStats()`. CLIB labels every kind that isn't 대출 or
  반납 as 연체, so reservations (2) showed as 연체; here they are 예약. Its 회원명 label showed
  the 회원번호; here it shows the name. A book whose barcode was reused counts once (the
  current book first).
- **번호변경 (등급별 회원번호관리):** `UserCodeDlg.ReUserCode()`. The grade's 구분기호 and the
  next number, worked out as 신규 does when numbering by grade (deleted members' numbers
  count; none yet gives 구분기호 + 00000001). Moves USERS, BOOK_LENT (USERS, ATTACH_USER,
  RESERVE_USER), RENTAL_HISTORY, RESERVATION and ATTACH_HISTORY to the new number. CLIB takes
  the letters of the highest number that starts with the 구분기호, so a longer prefix (AB for
  A) could carry over; here only the 구분기호 is kept.
- **삭제한 회원번호관리:** `DeleteUsers`. 삭제 removes the deleted member's USERS rows and the
  RENTAL_HISTORY up to its deletion (CLIB builds the ATTACH_HISTORY delete but never runs
  it; neither does this). 삭제취소 is refused while another member has the number; CLIB
  restores every deleted row with the number, this only the latest, so a number deleted twice
  doesn't become two members. The web asks once before 일괄삭제, which CLIB does without asking.
- **Marc 파일 저장:** `SaveFileProcess.SaveMarcFileThFn()`. A saved book gives its stored
  record unchanged; a book edited in the list but not saved, or a new one, is written with its
  changes as saving would (without saving it). Records end with the record terminator; with
  CRLF a line break goes between them (CLIB can also leave one after the last).

## Settings

`settings_store.py` ports what CLIB's settings screens save. `changes` holds any of these
sections, each written in one transaction:

| section | screen | where it goes |
|---|---|---|
| `lend` | 대출환경설정 | LENT_OPTION |
| `grades` | 대출기간설정 / 회원등급설정 | CODE_SUB 000 (names) and USER_LEVEL (구분기호, days, limits); a new grade gets CLIB's 5 books, 7 days, 3 reservations |
| `userCodeByGrade` | 회원등급설정 | USERCODE |
| `book` | 도서관리설정 | AUTHORCODE, AUTHOR, BOOK, MOUM, TOTAL, PUBLISH, ISBN_SEARCH; CODE_SUB 002 (소장위치) |
| `bankbook` | 독서통장 설정 | BANKBOOK_OPTION |
| `library` | 도서관 설정 | LIBRARY name, phone, address, email (never the password) |
| `card` | 회원증 출력 (saved when printing) | LIBRARY.NOTICE (title, notice, card name, tab-separated); CARD_LEFTMARGIN, CARD_TOPMARGIN, CARD_OUTLINE |
| `claim` | 청구기호 출력 (saved when printing; the v./c. boxes when ticked) | CLAIM_LABEL, CLAIM_OUTLINE, CLAIM_ALIGN, CLAIM_BARCODE, CLAIM_LEFTMARGIN, CLAIM_TOPMARGIN, CLAIM_FONT, CLAIM_FONTSIZE, CLAIM_V, CLAIM_C, CLAIM_VUPPER, CLAIM_CUPPER (CLAIM_LOCATION is read, never saved, as in CLIB) |

The upper-case keys (USERCODE, AUTHORCODE, …) are what CLIB keeps in `CLIB.exe.Config`.
The server doesn't write that file (it sits read-only in Program Files and holds CLIB's
connection settings). They go to `server/clib_settings.json` (not in git)
instead, written only after the database part has committed, and read on top of
CLIB.exe.Config. Delete that file to go back to CLIB's own values. So these settings, changed
on the web, apply to the web only; CLIB.exe keeps its own.

Checks follow CLIB's messages (at least one grade and one location, grade names unique,
구분기호 when numbering by grade), plus two of its own: a grade that members still have,
or a location that books still use, can't be removed. CLIB allows both and leaves those
members or books without a grade or location.

## Backup and restore

`backup.py` ports BookDream's `DataBackUp()`, `AutoBackup()`, `DefaultBackup()`, the
`Set_Backup` dialog and the separate `DataRestore.exe`. LocalDB writes and reads the .bak
files itself, through a connection to `master`.

- **데이터백업:** `BACKUP DATABASE` into the backup folder as `yyyyMMdd_HHmmss.bak` (CLIB
  uses a 12-hour clock there); the browser downloads a copy, which stands in for CLIB's save
  dialog.
- **데이터복구:** checks the file with `RESTORE FILELISTONLY`, backs up the current data as
  `…_before_restore.bak`, sets the database `SINGLE_USER WITH ROLLBACK IMMEDIATE` (CLIB, the
  kiosk and the server's own open requests are disconnected; CLIB asks you to close it
  instead), then `RESTORE … WITH REPLACE`, moving the files to where this database keeps them,
  and back to `MULTI_USER`. Other API requests get 503 meanwhile, and CLIB's daily checks run
  again on the restored data. CLIB's DataRestore drops the database and restores to the paths
  inside the backup, so a backup from another PC or from `CLIB_WEB` couldn't be restored there.
- **자동백업설정:** 자동백업 사용하기, 백업위치, 백업주기 (days) and 백업시점 (실행 및 종료시 /
  실행시 / 종료시). CLIB keeps them in its user settings; the server keeps them in
  `clib_settings.json` (AUTOBACKUP, BACKUPPATH, BACKUPDATE, BACKUPRUN, LAST). "실행" is the
  server starting, and each new day for a server that keeps running; "종료" is stopping it
  with Ctrl+C. A backup is due when the 백업주기 has passed since the last (or the last was
  today, which CLIB refreshes). Automatic backups are named `…_auto.bak`, and only those of
  the same day are replaced; CLIB deletes every backup of the day in that folder, manual ones
  too. A web page can't browse the server's folders, so 백업위치 is typed.
- **CLIB's safety copies:** like CLIB starting and exiting, the server writes
  `C:\CLIB\Data\AutoBackup\yyyyMMdd_ON.bak` when it starts and `_OFF.bak` when it stops,
  removing the two oldest once there are 20.

## Screens using the server

A screen uses the database when its logic has `server: true` (see `web/js/screens/`).
All the ported forms do: 대출, 반납, 예약, 이용현황, 회원관리, 회원검색, 회원증 출력, 도서관리,
도서 불러오기, 대출/반납 통계 and the settings dialogs (환경설정 and its four panels). The
table-only preview screens (도서보유현황, 연체관리, …) still show sample rows. The status
bar says which source a screen is using.

대출, 반납, 대출연장, 예약 and 예약취소 write to the database, and show CLIB's half-second
notice (LentMsg) afterwards. 회원관리 and 도서관리 save and delete, and every settings
screen saves. Only the 연체금 완납 button still answers that it can't be saved yet.

## Self-service kiosk (port 8081)

`web-self/` is CLIB_Self.exe on the web: a full-screen menu (대출, 반납, 검색) over CLIB_Self's own
images, with its idle timer (back to the menu after 60 s, 120 s on 도서검색). It uses the same
API as the library's app:

- 대출: the member number first (`GET /api/users/<id>`), then each book. `POST /api/lend` runs
  with `preview` for the "대출하시겠습니까?" dialog, then for real. The desk's questions are
  answered the way CLIB_Self works: 재대출 yes, 딸림자료 not lent with the book.
- 반납: a member number lists their books; anything else is returned as a book, with
  `answers.kiosk` (reserved books go to the desk) and the 딸림자료 left for the desk.
- 도서검색: `GET /api/search`.

Not ported: RFID readers, and 독서통장 members (refused, as at the desk).

## LocalDB after a restart

CLIB and CLIB_Self start LocalDB themselves. After such a restart the ODBC driver sometimes
stops finding `(localdb)\v11.0` by name while the instance runs fine. `db.connect()` then looks
up the instance's named pipe with `sqllocaldb info` and connects through it.

## Cloud download and upload (데이터베이스 관리 → 클라우드 다운로드 / 업로드)

`cloud.py`, after libServer's `downloadDB.py`: makes this server's database match the cloud
MongoDB (`library`: book, marc, user, rentLog, rent). Each table is compared with the cloud and
rows are added, changed or deleted in one transaction; a failure changes nothing. The `code`
collection is not downloaded (replacing CODE_SUB makes CLIB crash, as libServer found). A cloud
collection that comes back empty stops the download instead of emptying the table. After a
real download a "Download DB" entry goes to the cloud's `serverLog`.

`config.json` (keep it private; it holds the password):

```json
{ "cloud": { "connection": "mongodb+srv://USER:{}@HOST/...", "password": "...", "database": "library",
             "key": "-----BEGIN RSA PRIVATE KEY-----\n..." } }
```

`{}` in `connection` is where the password goes. Instead of copying the values,
`"libServerConfig": "C:\\path\\to\\libServer\\config.py"` reads them from libServer. With
neither, the server reads libServer's `config.py` one folder up (`..\config.py`), so a
libServer checkout needs no `config.json`.

| route | |
|---|---|
| `POST /api/cloud/download` `{test}` | start a download in the background; `test: true` only compares |
| `POST /api/cloud/upload` `{test, bookOnly}` | make the cloud match this server; `bookOnly` sends only books and MARC |
| `GET /api/cloud` | progress of the current job: mode, state, phase, startedAt / finishedAt / elapsed (seconds), and per table local / count / downloaded / add / change / delete / applied; `last`: the time of the last real download and upload (kept in `clib_settings.json`) |
| `GET /api/sequence` | the start or 종료 sequence: kind start / stop, state running / done / error / stopped, step backup / download / upload, the backup file, `canStop` |
| `POST /api/shutdown` | 종료: back up, upload, then stop the server (only when started by `run.bat`) |
| `GET /api/notices` | 게시판: the cloud's `notice` collection, newest first; `[{no, title, writeDate, content}]` |
| `POST /api/notices` `{title, writeDate, content}` | add a notice, numbered after the highest `_id` |
| `POST /api/notices/<no>` `{title, writeDate, content}` | change notice `no` |
| `POST /api/notices/<no>/delete` | delete notice `no` |

Upload (`cloud.upload`, after libServer's `uploadDB.py`) sends every table the download takes,
compared the same way and changed with inserts, deletes and `$set` updates. Only 대출 rows
for books that are out or reserved go up. 대출기록 goes to `rentLog` (kept equal) and new entries
also to `rentHistory` (append only). Each member's phone (digits) and e-mail go up as RSA
signatures (`encrypted_phone`, `encrypted_email`) made with `key`, the same as libServer's. The
cloud has no transaction, so an upload that fails partway is finished by running it again. An
empty local table stops the upload instead of emptying the cloud. Download and upload share one
job slot, so they never run at the same time.
