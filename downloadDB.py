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
import sys
import argparse
from datetime import datetime

from uiUtil import Progress

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

global shutdown

def downloadDatabase(clib, db, widgets, forced):
    print("Download database")

    result = dict()
    print("="*80)
    bookInfo = db.command("collstats", "book")
    widgets["book"].setCount(bookInfo['count'])
    print(f"Book ({bookInfo['count']})")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict, widgets["book"].setDownload, 10)
    result["book"] = {"count": len(books)}

    print("="*80)
    marcInfo = db.command("collstats", "marc")
    widgets["marc"].setCount(marcInfo['count'])
    print(f"MARC ({marcInfo['count']})")
    marcs = convertToSQL(db.marc, "SEQ", sqlMARCDict, widgets["marc"].setDownload, 10)
    result["marc"] = {"count": len(marcs)}
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
    result["user"] = {"count": len(users)}
    for key in users:
        user = users[key]
        if 'DELETE_YN' not in user:
            user['DELETE_YN'] = "N"

    print("="*80)
    rentLogInfo = db.command("collstats", "rentLog")
    widgets["rentHistory"].setCount(rentLogInfo['count'])
    print(f"RentHistory ({rentLogInfo['count']})")
    rentlog = convertToSQL(db.rentLog, "SEQ", sqlRentHistoryDict, widgets["rentHistory"].setDownload, 10)
    result["rentHistory"] = {"count": len(rentlog)}
    for entry in clib.rentHistory:
        regDate = entry['REG_DATE']
        if len(regDate) == 18:
            print(regDate)
            regDate = regDate[0:11] + "0" + regDate[11:]
            print(regDate)

    print("="*80)
    rentInfo = db.command("collstats", "rent")
    widgets["rent"].setCount(rentInfo['count'])
    print(f"Rent ({rentInfo['count']})")
    rents = convertToSQL(db.rent, "BARCODE", sqlRentDict, widgets["rent"].setDownload, 10)
    result["rent"] = {"count": len(rents)}
    for key in books:
        if key not in rents:
            rents[key] = {'SEQ': books[key]['SEQ'], 'BARCODE': key, 'STATS': 0, 'USERS': '', 'LENT_DATE': '', 'RETURN_DATE': '', 'RESERVE_USER': '', 'RESERVE_DATE': '', 'EXTEND_COUNT': 0, 'DELETE_YN': books[key]['DELETE_YN'], 'ATTACH': 'N', 'ATTACH_USER': ''}

    print("="*80)
    print("Update DBs")
#    updateDB(clib.books, books, clib, "book", "BARCODE", widgets["book"].setUpdate)
    print("Update books")
    updates = compare(books, clib.books, False)
    widgets["book"].setState(f"Add: {len(updates[0])} Changed: {len(updates[1])} Deleted: {len(updates[2])}")
    updateSQL(updates, books, clib, "book", "BARCODE", widgets["book"].setUpdate)
    result["book"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})

    print("Update marcs")
#    updateDB(clib.marcs, marcs, clib, "marc", "SEQ", widgets["marc"].setUpdate)
    updates = compare(marcs, clib.marcs, False)
    widgets["marc"].setState(f"Add: {len(updates[0])} Changed: {len(updates[1])} Deleted: {len(updates[2])}")
    updateSQL(updates, marcs, clib, "marc", "SEQ", widgets["marc"].setUpdate)
    result["marc"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})

    print("Update users")
#    updateDB(clib.users, users, clib, "users", "USER_CODE", widgets["user"].setUpdate)
    updates = compare(users, clib.users, False)
    widgets["user"].setState(f"Add: {len(updates[0])} Changed: {len(updates[1])} Deleted: {len(updates[2])}")
    updateSQL(updates, users, clib, "users", "USER_CODE", widgets["user"].setUpdate)
    result["user"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})

    print("Update rent histories")
#    updateDB(list2dict(clib.rentHistory, "SEQ"), rentlog, clib, "rental_history", "SEQ", widgets["rent"].setUpdate)
    currDb = list2dict(clib.rentHistory, "SEQ")
    updates = compare(rentlog, currDb, False)
    widgets["rentHistory"].setState(f"Add: {len(updates[0])} Changed: {len(updates[1])} Deleted: {len(updates[2])}")
    result["rentHistory"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})
    mismatch = False
    if len(updates[2]) > 0:
        mismatch = True
    for key in updates[1]:
        src = rentlog[key]
        dst = currDb[key]
        if (src["SEQ"] != dst["SEQ"] or src["BOOK_CODE"] != dst["BOOK_CODE"] or
            src["USER_CODE"] != dst["USER_CODE"]):
            print("Mismatch")
            print(src)
            print(dst)
            mismatch = True
            break
    if not forced and mismatch:
        widgets["rentHistory"].setState(f"Cannot update rent history")
        return result

    updateSQL(updates, rentlog, clib, "rental_history", "SEQ", widgets["rentHistory"].setUpdate)

    print("Update rents")
#    updateDB(clib.rents, rents, clib, "book_lent", "BARCODE", widgets["rent"].setUpdate)
    updates = compare(rents, clib.rents, False)
    result["rent"].update({"add": len(updates[0]), "change": len(updates[1]), "delete": len(updates[2])})
    widgets["rent"].setState(f"Add: {len(updates[0])} Changed: {len(updates[1])} Deleted: {len(updates[2])}")
    updateSQL(updates, rents, clib, "book_lent", "BARCODE", widgets["rent"].setUpdate)

    checkUnique(rentlog, "SEQ")

    return result

def downloadThread(window, widgets, forced):
    global shutdown
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library
    print("Check")

    result = downloadDatabase(clib, db, widgets, forced)
    print("Done")

    print("Report Server Log")
    reportServerLog(db, "Download DB", result)

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
    args = parser.parse_args()

    forced = args.force
    print(forced)

    shutdown = False
    window = tk.Tk()
    window.title("DB download")
    window.geometry('800x400')

    downloadLabel = tk.Label(window, text="Download Cloud DB")
    updateLabel = tk.Label(window, text="Update CLIB DB")

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

    thread = threading.Thread(target = downloadThread, args = (window, widgets, forced))
    thread.start()

    window.after(1000, timer)
    window.mainloop()
    print("Close main")
