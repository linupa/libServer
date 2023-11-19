import sys
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

def updateMongoDB(mdb, srcDB, callback1 = None, callback2 = None, log = False, debug = False):
    mdbDict = mdb2dict(mdb, callback=callback1)
    updates = compare(srcDB, mdbDict, log=log)
    if not debug:
        updateCloud(updates, srcDB, mdb, callback=callback2)

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

def uploadDatabase(clib, db, debug = False):
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
    print("Upload database")
    books = convertToMDB(clib.books, '_id', sqlBookDict)
    marcs = convertToMDB(clib.marcs, '_id', sqlMARCDict)
    users = convertToMDB(clib.users, '_id', sqlUserDict)
    rents = convertToMDB(clib.rents, '_id', sqlRentDict)
    rentlog = convertToMDB(clib.rentHistory, '_id', sqlRentHistoryDict)

    # Remove AVAILBLE books from rent list
    for key in list(rents.keys()):
        if rents[key]['state'] in {0, "0"}:
            del rents[key]

    print("="*80)
    bookInfo = db.command("collstats", "book")
    bookCount = bookInfo['count']
    print(f"Book ({bookInfo['count']})")
    updateMongoDB(db.book, books, debug = debug, callback1=setBookProgress, callback2=setBookUpdate)

    print("="*80)
    marcInfo = db.command("collstats", "marc")
    marcCount = marcInfo['count']
    print(f"MARC ({marcInfo['count']})")
    matchCount = 0
    mismatchCount = 0
    failCount = 0
    for key in marcs:
        orgMarc = marcs[key]["MARC_DATA"]
        try:
            marc = MARC(orgMarc, debug=False)
            marc.decode()
            marc.check()
            newMarc = marc.encode()
            marcs[key]["MARC_DATA"] = newMarc
            if bytes(orgMarc, "UTF-8") != bytes(newMarc, "UTF-8"):
                mismatchCount += 1
            else:
                matchCount += 1
        except Exception as e:
            print(f"Failed to decode MARC {e}")
            print(orgMarc)
            failCount += 1
    print(f"Same {matchCount} / Change {mismatchCount} / Fail {failCount} / Total {len(marcs)}")
    updateMongoDB(db.marc, marcs, debug = debug, callback1=setMARCProgress, callback2=setMARCUpdate)

    print("="*80)
    userInfo = db.command("collstats", "user")
    userCount = userInfo['count']
    print(f"User ({userInfo['count']})")
    encryptUserInfo(users)

    updateMongoDB(db.user, users, debug = debug, callback1=setUserProgress, callback2=setUserUpdate)

    print("="*80)
    rentLogInfo = db.command("collstats", "rentLog")
    rentLogCount = rentLogInfo['count']
    print(f"RentHistory ({rentLogInfo['count']})")
    rentlog = dict2list(rentlog)
    keyMap = {"idx": "_id", "book": "book_id", "state": "book_state", "user": "user_id", "date": "timestamp", "retDate": "return_date"}
    checkRentHistory(rentlog, keyMap)
    rentlog = list2dict(rentlog)
    updateMongoDB(db.rentLog, rentlog, log=True, debug = debug, callback1=setRentLogProgress, callback2=setRentLogUpdate)

    print("="*80)
    rentInfo = db.command("collstats", "rent")
    rentCount = rentInfo['count']
    print(f"Rent ({rentInfo['count']})")
    updateMongoDB(db.rent, rents, debug = debug, callback1=setRentProgress, callback2=setRentUpdate)

def uploadThread(window):
    global shutdown
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    debug = False
    if len(sys.argv) >= 2 and sys.argv[1] == "debug":
        debug = True

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library

    uploadDatabase(clib, db, debug = debug)
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
    window.geometry('800x300')

    downloadLabel = tk.Label(window, text="Download Cloud DB")
    uploadLabel = tk.Label(window, text="Upload Cloud DB")

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

    downloadLabel.grid(column = 0, row = 0)
    uploadLabel.grid(column = 0, row = 6)
    bookLabel.grid(column = 0, row = 1)
    marcLabel.grid(column = 0, row = 2)
    userLabel.grid(column = 0, row = 3)
    rentLabel.grid(column = 0, row = 4)
    rentLogLabel.grid(column = 0, row = 5)

    bookProgress.grid(column = 1, row = 1)
    marcProgress.grid(column = 1, row = 2)
    userProgress.grid(column = 1, row = 3)
    rentProgress.grid(column = 1, row = 4)
    rentLogProgress.grid(column = 1, row = 5)

    bookLabel2.grid(column = 0, row = 7)
    marcLabel2.grid(column = 0, row = 8)
    userLabel2.grid(column = 0, row = 9)
    rentLabel2.grid(column = 0, row = 10)
    rentLogLabel2.grid(column = 0, row = 11)

    bookUpdate.grid(column = 1, row = 7)
    marcUpdate.grid(column = 1, row = 8)
    userUpdate.grid(column = 1, row = 9)
    rentUpdate.grid(column = 1, row = 10)
    rentLogUpdate.grid(column = 1, row = 11)

    thread = threading.Thread(target = uploadThread, args = (window,))
    thread.start()

    window.after(1000, timer)
    window.mainloop()
