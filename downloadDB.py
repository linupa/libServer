#!/bin/python3

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

def downloadDatabase(clib, db, widgets):
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
    widgets["book"].setCount(bookInfo['count'])
    bookCount = bookInfo['count']
    print(f"Book ({bookInfo['count']})")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict, widgets["book"].setDownload, 10)

    print("="*80)
    marcInfo = db.command("collstats", "marc")
    widgets["marc"].setCount(marcInfo['count'])
    marcCount = marcInfo['count']
    print(f"MARC ({marcInfo['count']})")
    marcs = convertToSQL(db.marc, "SEQ", sqlMARCDict, widgets["marc"].setDownload, 10)
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
    widgets["user"].setCount(userInfo['count'])
    print(f"User ({userInfo['count']})")
    users = convertToSQL(db.user, "USER_CODE", sqlUserDict, widgets["user"].setDownload, 10)
    for key in users:
        user = users[key]
        if 'DELETE_YN' not in user:
            user['DELETE_YN'] = "N"

    print("="*80)
    rentInfo = db.command("collstats", "rent")
    widgets["rent"].setCount(rentInfo['count'])
    print(f"User ({userInfo['count']})")
    rentCount = rentInfo['count']
    print(f"Rent ({rentInfo['count']})")
    rents = convertToSQL(db.rent, "BARCODE", sqlRentDict, widgets["rent"].setDownload, 10)
    for key in books:
        if key not in rents:
            rents[key] = {'SEQ': books[key]['SEQ'], 'BARCODE': key, 'STATS': 0, 'USERS': '', 'LENT_DATE': '', 'RETURN_DATE': '', 'RESERVE_USER': '', 'RESERVE_DATE': '', 'EXTEND_COUNT': 0, 'DELETE_YN': books[key]['DELETE_YN'], 'ATTACH': 'N', 'ATTACH_USER': ''}

    print("="*80)
    rentLogInfo = db.command("collstats", "rentLog")
    widgets["rentHistory"].setCount(rentLogInfo['count'])
    rentLogCount = rentLogInfo['count']
    print(f"RentHistory ({rentLogInfo['count']})")
    rentlog = convertToSQL(db.rentLog, "SEQ", sqlRentHistoryDict, widgets["rentHistory"].setDownload, 10)
    for entry in clib.rentHistory:
        regDate = entry['REG_DATE']
        if len(regDate) == 18:
            print(regDate)
            regDate = regDate[0:11] + "0" + regDate[11:]
            print(regDate)

    print("="*80)
    print("Update DBs")
    updateDB(clib.books, books, clib, "book", "BARCODE", widgets["book"].setUpdate)
    updateDB(clib.marcs, marcs, clib, "marc", "SEQ", widgets["marc"].setUpdate)
    updateDB(clib.users, users, clib, "users", "USER_CODE", widgets["user"].setUpdate)
    updateDB(clib.rents, rents, clib, "book_lent", "BARCODE", widgets["rent"].setUpdate)
    updateDB(list2dict(clib.rentHistory, "SEQ"), rentlog, clib, "rental_history", "SEQ", widgets["rent"].setUpdate)

    checkUnique(rentlog, "SEQ")

def downloadThread(window, widgets):
    global shutdown
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library
    print("Check")

    downloadDatabase(clib, db, widgets)
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

class Progress:
    def __init__(self, window, name):
        self.window = window
        self.bookLabel = tk.Label(window, text=name)
        self.bookProgress = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
        self.bookLabel2 = tk.Label(window, text=name)
        self.bookUpdate = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
        self.count = 1

    def setCount(self, count):
        self.count = count

    def addDownload(self, index):
        self.bookLabel.grid(column = 0, row = index)
        self.bookProgress.grid(column = 1, row = index)

    def addUpdate(self, index):
        self.bookLabel2.grid(column = 0, row = index)
        self.bookUpdate.grid(column = 1, row = index)

    def setDownload(self, value):
        self.bookProgress["value"] = 100 * value / self.count

    def setUpdate(self, value):
        self.bookUpdate["value"] = value

if __name__ == '__main__':
    global shutdown

    shutdown = False
    window = tk.Tk()
    window.title("DB download")
    window.geometry('800x400')

    downloadLabel = tk.Label(window, text="Download Cloud DB")
    updateLabel = tk.Label(window, text="Update CLIB DB")

    items = ["book", "marc", "user", "rent", "rentHistory"]
    widgets = dict()
    widgets["book"] = Progress(window, "Book")
    widgets["marc"] = Progress(window, "MARC")
    widgets["user"] = Progress(window, "User")
    widgets["rent"] = Progress(window, "Rent")
    widgets["rentHistory"] = Progress(window, "RentHistory")

    index = 0
    for i in range(len(items)):
        widgets[items[i]].addDownload(index)
        index += 1


    index += 1
    for i in range(len(items)):
        widgets[items[i]].addUpdate(index)
        index += 1

    thread = threading.Thread(target = downloadThread, args = (window, widgets))
    thread.start()

    window.after(1000, timer)
    window.mainloop()
    print("Close main")
