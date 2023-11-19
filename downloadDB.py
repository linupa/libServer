from pymongo import MongoClient
from config import Config
from clibrary import CLibrary
from dbUtil import *
from marc import MARC

import tkinter as tk
import threading
from tkinter import ttk
import time

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

global bookCount
global bookProgress
global marcCount
global marcProgress
global userCount
global userProgress
global rentCount
global rentProgress
global rentLogCount
global rentLogProgress
global shutdown

def updateDB(currDb, srcDb, dstDb, dbName, dbKey, callback = None, log = False):
    updates = compare(srcDb, currDb, log=log)
    updateSQL(updates, srcDb, dstDb, dbName, dbKey, callback)

def setBookProgress(value):
    global bookCount
    global bookProgress
    bookProgress["value"] = 100 * value / bookCount

def setMARCProgress(value):
    global marcCount
    global marcProgress
    marcProgress["value"] = 100 * value / marcCount

def setUserProgress(value):
    global userCount
    global userProgress
    userProgress["value"] = 100 * value / userCount

def setRentProgress(value):
    global rentCount
    global rentProgress
    rentProgress["value"] = 100 * value / rentCount

def setRentLogProgress(value):
    global rentLogCount
    global rentLogProgress
    rentLogProgress["value"] = 100 * value / rentLogCount

def setBookUpdate(value):
    global bookCount
    global bookUpdate
    bookUpdate["value"] = value

def setMARCUpdate(value):
    global marcCount
    global marcUpdate
    marcUpdate["value"] = value

def setUserUpdate(value):
    global userCount
    global userUpdate
    userUpdate["value"] = value

def setRentUpdate(value):
    global rentCount
    global rentUpdate
    rentUpdate["value"] = value

def setRentLogUpdate(value):
    global rentLogCount
    global rentLogUpdate
    rentLogUpdate["value"] = value

def downloadDatabase(clib, db):
    global bookCount
    global bookProgress
    global marcCount
    global marcProgress
    global userCount
    global userProgress
    global rentCount
    global rentProgress
    global rentLogCount
    global rentLogProgress
    print("Download database")

#    for key in books:
#        book = books[key]
#        if "MOD_DATE" not in book or len(book["MOD_DATE"]) == 0:
#            print(book)
#            book["MOD_DATE"] = book["REG_DATE"]
#            print(books[key])

    print("="*80)
    bookInfo = db.command("collstats", "book")
    bookCount = bookInfo['count']
    print(f"Book ({bookInfo['count']})")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict, setBookProgress, 10)

    print("="*80)
    marcInfo = db.command("collstats", "marc")
    marcCount = marcInfo['count']
    print(f"MARC ({marcInfo['count']})")
    marcs = convertToSQL(db.marc, "SEQ", sqlMARCDict, setMARCProgress, 10)
    matchCount = 0
    mismatchCount = 0
    failCount = 0
    for key in books:
        book = books[key]
        seq = book["SEQ"]
        orgMarc = marcs[seq]["MARC_DATA"]
        try:
            marc = MARC(orgMarc, debug=False)
            marc.decode()
            marc.check()
            newMarc = marc.encode()
            marcs[seq]["MARC_DATA"] = newMarc
            if bytes(orgMarc, "UTF-8") != bytes(newMarc, "UTF-8"):
                print("=" * 30 + "Mismatch" + "="*30)
                print(f"{len(orgMarc)} [{orgMarc}]")
                print(f"{len(newMarc)} [{newMarc}]")
                mismatchCount += 1
                for i in range(len(orgMarc)):
                    if orgMarc[i] != newMarc[i]:
                        print(f"{i}: {orgMarc[i]} - {newMarc[i]}")
                        break
            else:
                matchCount += 1
            bookInfo = marc.getBookInfo()
            if bookInfo["BARCODE"] == key:
                book.update(bookInfo)
            else:
                print(f"ERROR: barcode does not match")
                print(books[key])
                print(mercs[seq])
        except Exception as e:
            print(f"Failed to decode MARC {e}")
            print(orgMarc)
            failCount += 1
    print(f"Same {matchCount} / Change {mismatchCount} / Fail {failCount} / Total {len(marcs)}")



    print("="*80)
    userInfo = db.command("collstats", "user")
    userCount = userInfo['count']
    print(f"User ({userInfo['count']})")
    users = convertToSQL(db.user, "USER_CODE", sqlUserDict, setUserProgress, 10)
    for key in users:
        user = users[key]
        if 'DELETE_YN' not in user:
            user['DELETE_YN'] = "N"

    print("="*80)
    rentInfo = db.command("collstats", "rent")
    rentCount = rentInfo['count']
    print(f"Rent ({rentInfo['count']})")
    rents = convertToSQL(db.rent, "BARCODE", sqlRentDict, setRentProgress, 10)
    for key in books:
        if key not in rents:
            rents[key] = {'SEQ': books[key]['SEQ'], 'BARCODE': key, 'STATS': 0, 'USERS': '', 'LENT_DATE': '', 'RETURN_DATE': '', 'RESERVE_USER': '', 'RESERVE_DATE': '', 'EXTEND_COUNT': 0, 'DELETE_YN': books[key]['DELETE_YN'], 'ATTACH': 'N', 'ATTACH_USER': ''}

    print("="*80)
    rentLogInfo = db.command("collstats", "rentLog")
    rentLogCount = rentLogInfo['count']
    print(f"RentHistory ({rentLogInfo['count']})")
    rentlog = convertToSQL(db.rentLog, "SEQ", sqlRentHistoryDict, setRentLogProgress, 10)
    for entry in clib.rentHistory:
        regDate = entry['REG_DATE']
        if len(regDate) == 18:
            print(regDate)
            regDate = regDate[0:11] + "0" + regDate[11:]
            print(regDate)

    print("="*80)
    print("Update DBs")
    updateDB(clib.books, books, clib, "book", "BARCODE", setBookUpdate)
    updateDB(clib.marcs, marcs, clib, "marc", "SEQ", setMARCUpdate)
    updateDB(clib.users, users, clib, "users", "USER_CODE", setUserUpdate)
    updateDB(clib.rents, rents, clib, "book_lent", "BARCODE", setRentUpdate)
    updateDB(list2dict(clib.rentHistory, "SEQ"), rentlog, clib, "rental_history", "SEQ", setRentLogUpdate)

    checkUnique(rentlog, "SEQ")

def downloadThread(window):
    global shutdown
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library
    print("Check")

    downloadDatabase(clib, db)
    print("Done")
    time.sleep(3)

    print("Close")
#    window.destroy()
    shutdown = True
    print("Exit thread")

def timer():
    if shutdown:
        window.destroy()
    else:
        window.after(1000, timer)


if __name__ == '__main__':
    global shutdown

    shutdown = False
    window = tk.Tk()
    window.title("DB download")
    window.geometry('800x800')

    bookLabel = tk.Label(window, text="Book")
    marcLabel = tk.Label(window, text="MARC")
    userLabel = tk.Label(window, text="User")
    rentLabel = tk.Label(window, text="Rent")
    rentLogLabel = tk.Label(window, text="RentHistory")

    bookProgress = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
    marcProgress = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
    userProgress = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
    rentProgress = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
    rentLogProgress = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)

    bookLabel2 = tk.Label(window, text="Book")
    marcLabel2 = tk.Label(window, text="MARC")
    userLabel2 = tk.Label(window, text="User")
    rentLabel2 = tk.Label(window, text="Rent")
    rentLogLabel2 = tk.Label(window, text="RentHistory")

    bookUpdate = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
    marcUpdate = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
    userUpdate = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
    rentUpdate = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
    rentLogUpdate = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)

    bookLabel.grid(column = 0, row = 0)
    marcLabel.grid(column = 0, row = 1)
    userLabel.grid(column = 0, row = 2)
    rentLabel.grid(column = 0, row = 3)
    rentLogLabel.grid(column = 0, row = 4)

    bookProgress.grid(column = 1, row = 0)
    marcProgress.grid(column = 1, row = 1)
    userProgress.grid(column = 1, row = 2)
    rentProgress.grid(column = 1, row = 3)
    rentLogProgress.grid(column = 1, row = 4)

    bookLabel2.grid(column = 0, row = 6)
    marcLabel2.grid(column = 0, row = 7)
    userLabel2.grid(column = 0, row = 8)
    rentLabel2.grid(column = 0, row = 9)
    rentLogLabel2.grid(column = 0, row = 10)

    bookUpdate.grid(column = 1, row = 6)
    marcUpdate.grid(column = 1, row = 7)
    userUpdate.grid(column = 1, row = 8)
    rentUpdate.grid(column = 1, row = 9)
    rentLogUpdate.grid(column = 1, row = 10)

    thread = threading.Thread(target = downloadThread, args = (window,))
    thread.start()

    window.after(1000, timer)
    window.mainloop()
    print("Close main")
