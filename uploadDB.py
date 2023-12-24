import sys
from pymongo import MongoClient
from config import Config
from clibrary import CLibrary
from dbUtil import *
from marc import MARC
from uiUtil import Progress

import tkinter as tk
import threading
from tkinter import ttk
import time
import argparse

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

global shutdown

def updateMongoDB(mdb, srcDB, widget, log = False, debug = False):
    mdbDict = mdb2dict(mdb, callback=widget.setDownload)
    updates = compare(srcDB, mdbDict, log=log)
    widget.setState(f"Add: {len(updates[0])} Changed: {len(updates[1])} Deleted: {len(updates[2])}")
    if not debug:
        updateCloud(updates, srcDB, mdb, callback=widget.setUpdate)

    return updates

def uploadDatabase(clib, db, widgets, forced, debug = False):
    print("Upload database")
    books = convertToMDB(clib.books, '_id', sqlBookDict)
    marcs = convertToMDB(clib.marcs, '_id', sqlMARCDict)
    users = convertToMDB(clib.users, '_id', sqlUserDict)
    rents = convertToMDB(clib.rents, '_id', sqlRentDict)
    rentlog = convertToMDB(clib.rentHistory, '_id', sqlRentHistoryDict)
    result = dict()
    result["book"] = {"count": len(books)}
    result["marc"] = {"count": len(marcs)}
    result["user"] = {"count": len(users)}
    result["rent"] = {"count": len(rents)}
    result["rentHistory"] = {"count": len(rentlog)}

    # Remove AVAILBLE books from rent list
    for key in list(rents.keys()):
        if rents[key]['state'] in {0, "0"}:
            del rents[key]

    print("="*80)
    bookInfo = db.command("collstats", "book")
    print(f"Book ({bookInfo['count']})")
    updates = updateMongoDB(db.book, books, widgets["book"], debug = debug)
    result["book"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})

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
    updates = updateMongoDB(db.marc, marcs, widgets["marc"], debug = debug)
    result["marc"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})

    print("="*80)
    userInfo = db.command("collstats", "user")
    userCount = userInfo['count']
    print(f"User ({userInfo['count']})")
    encryptUserInfo(users)

    updates = updateMongoDB(db.user, users, widgets["user"], debug = debug)
    result["user"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})

    print("="*80)
    rentLogInfo = db.command("collstats", "rentLog")
    rentLogCount = rentLogInfo['count']
    print(f"RentHistory ({rentLogInfo['count']})")
    rentlog = dict2list(rentlog)
    keyMap = {"idx": "_id", "book": "book_id", "state": "book_state", "user": "user_id", "date": "timestamp", "retDate": "return_date"}
    checkRentHistory(rentlog, keyMap)
    print(rentlog[0])
    rentlog = list2dict(rentlog)
#    updates = updateMongoDB(db.rentLog, rentlog, widgets["rentHistory"], log=True, debug = debug)
#              updateMongoDB(mdb, srcDB, widget, log = False, debug = False):
    mdb = db.rentLog
    srcDB = rentlog
    widget = widgets["rentHistory"]
    mdbDict = mdb2dict(mdb, callback=widget.setDownload)
    updates = compare(srcDB, mdbDict, log=True)
    result["rentHistory"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})
    mismatch = False
    if len(updates[2]) > 0:
        mismatch = True
    for key in updates[1]:
        src = rentlog[key]
        dst = currDb[key]
        if (src["_id"] != dst["_id"] or src["book_id"] != dst["book_id"] or
            src["user_id"] != dst["user_id"]):
            print("Mismatch")
            print(src)
            print(dst)
            mismatch = True
            break
    widget.setState(f"Add: {len(updates[0])} Changed: {len(updates[1])} Deleted: {len(updates[2])}")
    if (forced or not mismatch) and not debug:
        updateCloud(updates, srcDB, mdb, callback=widget.setUpdate)

    print("="*80)
    rentInfo = db.command("collstats", "rent")
    rentCount = rentInfo['count']
    print(f"Rent ({rentInfo['count']})")
    updates = updateMongoDB(db.rent, rents, widgets["rent"], debug = debug)
    result["rent"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})

    return result

def uploadThread(window, widgets, forced, debug):
    global shutdown
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library

    result = uploadDatabase(clib, db, widgets, forced, debug = debug)
    print("Done")

    print("Report Server Log")
    reportServerLog(db, "Upload DB", result)

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

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    forced = args.force
    debug = args.debug
    print(f"forced: {forced} debug: {debug}")

    shutdown = False
    window = tk.Tk()
    window.title("DB upload")
    window.geometry('800x400')

    downloadLabel = tk.Label(window, text="Download Cloud DB")
    uploadLabel = tk.Label(window, text="Upload Cloud DB")

    items = ["book", "marc", "user", "rentHistory", "rent"]
    widgets = dict()
    widgets["book"] = Progress(window, "Book")
    widgets["marc"] = Progress(window, "MARC")
    widgets["user"] = Progress(window, "User")
    widgets["rentHistory"] = Progress(window, "RentHistory")
    widgets["rent"] = Progress(window, "Rent")

    index = 0
    for i in range(len(items)):
        widgets[items[i]].addDownload(index)
        index += 1

    index += 1
    for i in range(len(items)):
        widgets[items[i]].addUpdate(index)
        index += 2

    thread = threading.Thread(target = uploadThread, args = (window, widgets, forced, debug))
    thread.start()

    window.after(1000, timer)
    window.mainloop()
