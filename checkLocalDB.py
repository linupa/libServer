from clibrary import CLibrary
from dbUtil import *

if __name__ == '__main__':
    clib = CLibrary()
    print("Got clib")
    print(len(clib.books))
    print(len(clib.rentHistory))

    rentHistory = clib.rentHistory.copy()
    print(type(rentHistory))
    rentHistory.sort(key=lambda e : logKey(e,"REG_DATE"))

    print(f"Check Rent History")
    keyMap = {"idx": "SEQ", "book":"BOOK_CODE", "state": "BOOK_STATE", "user" : "USER_CODE", "date" : "REG_DATE", "retDate": "retDate"}
    checkRentHistory(rentHistory, keyMap = keyMap, db = None, checkId = False)
    duplicates = checkUnique(rentHistory, key="SEQ")
    print(duplicates)
    dupHistory = dict()
    for dup in duplicates:
        dupHistory[dup] = rentHistory[dup]
    print(f"Delete {duplicates}")
    updateSQL([list(), list(), duplicates], dupHistory, clib, "rental_history", "SEQ")
#    print(f"Add {duplicates}")
#    updateSQL([duplicates, list(), list()], dupHistory, clib, "rental_history", "SEQ")
