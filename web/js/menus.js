// Tab strip and toolbars, following CLIB's TopMenu/*.cs and BookDream.Select*Menu().
// An item opens a docked `view` (fills the workspace), a `dialog` (floating window),
// or both (CLIB switches to 도서관리 before opening most book dialogs).
// Items whose screens are not ported yet (no form or no logic) are shown disabled.
// 도서관리 and 회원관리 have no toolbar button of their own: the tab opens them, and every
// item on those toolbars works on that page.
window.CLIB_MENUS = {
  tabs: [
    { id: "lent", label: "대출/반납", items: [
      { label: "대출", icon: "lend", view: "BookLent" },
      { label: "반납", icon: "return", view: "BookReturn" },
      { label: "예약", icon: "reserve", view: "BookReserve" },
      { label: "이용현황", icon: "list", view: "LentStats" },
      { label: "연체관리", icon: "overdue", dialog: "BookDelay" },
      { label: "대출환경설정", icon: "setting", dialog: "LentOptionDlg" },
      { label: "환경설정", icon: "gear", dialog: "OptionDlg" },
    ] },
    { id: "book", label: "도서관리", items: [
      // CLIB's 도서검색 button calls SelectBookMenu(1), the same as 저장된 도서불러오기
      { label: "도서검색", icon: "search", view: "BookManage", dialog: "SearchMarc" },
      { label: "불러오기", icon: "load", children: [
        { label: "저장된 도서불러오기", view: "BookManage", dialog: "SearchMarc" },
        { label: "Marc 파일 불러오기", view: "BookManage", dialog: "MarcErrorMsg" },
        { label: "엑셀 파일 불러오기" },
      ] },
      // SaveFileProcess(mode): Marc 파일 저장 first asks about line breaks (CRLFDlg)
      { label: "파일로 저장", icon: "save", children: [
        { label: "Marc 파일 저장", view: "BookManage", dialog: "CRLFDlg" },
        { label: "엑셀파일 저장", view: "BookManage", dialog: "SaveFileProcess" },
      ] },
      { label: "중복체크", icon: "overlap", children: [
        { label: "ISBN 중복체크", view: "BookManage", dialog: "CheckISBNDlg" },
        { label: "청구기호 중복체크", view: "BookManage", dialog: "CheckClaimDlg" },
      ] },
      { label: "장서점검", icon: "check", view: "BookManage", dialog: "CheckBooksDlg" },
      { label: "일괄수정", icon: "edit", children: [
        { label: "별치기호 일괄수정" }, { label: "저자기호 일괄수정" },
        { label: "분류기호 일괄수정" }, { label: "소장위치 일괄수정" },
        { label: "반입구분 일괄수정" }, { label: "도서상태 일괄수정" },
      ] },
      { label: "도서배가", icon: "shelf", view: "OrderBook" },
      { label: "바코드출력", icon: "barcode", view: "BookManage", dialog: "InputBarcode" },
      // ClaimPrintView(): a window beside 도서관리's list, printing the checked books
      { label: "청구기호출력", icon: "label", view: "BookManage", dialog: "ClaimPrint" },
      { label: "도서관리설정", icon: "setting", dialog: "BookOptionDlg" },
      { label: "환경설정", icon: "gear", dialog: "OptionDlg" },
    ] },
    { id: "user", label: "회원관리", items: [
      { label: "회원검색", icon: "usersearch", view: "Users", dialog: "UserSearch" },
      // UserCardPrint() first asks which kind of card (SelectUserCard)
      { label: "회원증출력", icon: "card", view: "Users", dialog: "SelectUserCard" },
      // BatchUserState() / BatchUserLevel(): UserBatchDlg for the members checked in 회원관리
      { label: "일괄수정", icon: "edit", children: [
        { label: "회원상태 수정", view: "Users", dialog: "UserBatchState" },
        { label: "회원등급 수정", view: "Users", dialog: "UserBatchLevel" },
      ] },
      { label: "등급별 회원번호관리", icon: "idcode", dialog: "UserCodeDlg" },
      { label: "삭제한 회원번호관리", icon: "userdelete", dialog: "DeleteUsers" },
      { label: "회원등급설정", icon: "setting", dialog: "UserOptionDlg" },
      { label: "환경설정", icon: "gear", dialog: "OptionDlg" },
    ] },
    { id: "stats", label: "이용통계", items: [
      { label: "대출/반납통계", icon: "chart", view: "Lent_ReturnStats" },
      { label: "도서보유현황", icon: "books", view: "BookStats" },
      { label: "이용자현황", icon: "user", view: "UserStats" },
    ] },
    { id: "data", label: "데이터베이스 관리", items: [
      // Not CLIB's own 데이터복구: replaces the server's data with the cloud's (cloud.py)
      { label: "클라우드 다운로드", icon: "cloud", dialog: "CloudDownload" },
      { label: "클라우드 업로드", icon: "cloudUp", dialog: "CloudUpload" },
      // DataBackUp(), DataRestore.exe and Set_Backup (server/backup.py)
      { label: "데이터백업", icon: "backup", dialog: "DataBackup" },
      { label: "데이터복구", icon: "restore", dialog: "DataRestore" },
      { label: "자동백업설정", icon: "clock", dialog: "Set_Backup" },
    ] },
    { id: "board", label: "게시판", items: [
      { label: "게시판", icon: "board", view: "BoardFrm" },
    ] },
  ],

  // Dialogs a view or dialog opens from its own buttons, from the `new XxxDlg(` callers
  links: {
    RFID_Tagging: [["TagginFileOpen", "태깅파일 불러오기"]],
    BoardFrm: [["LogIn", "시작화면 공지"]],
  },

  // Docked views with no ported form, shown from their tables (none at the moment)
  composites: {},
};
