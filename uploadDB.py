import sys
from pymongo import MongoClient
from config import Config
from clibrary import CLibrary
from dbUtil import *
from marc import MARC

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

def updateMongoDB(mdb, srcDB, log = False, debug = False):
    mdbDict = mdb2dict(mdb)
    updates = compare(srcDB, mdbDict, log=log)
    if not debug:
        updateCloud(updates, srcDB, mdb)

def uploadDatabase(clib, db, debug = False):
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
    print("Book")
    updateMongoDB(db.book, books, debug = debug)

    print("="*80)
    print("MARC")
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
    updateMongoDB(db.marc, marcs, debug = debug)

    print("="*80)
    print("User")
    encryptUserInfo(users)

    updateMongoDB(db.user, users, debug = debug)

    print("="*80)
    print("RentHistory")
    rentlog = dict2list(rentlog)
    keyMap = {"idx": "_id", "book": "book_id", "state": "book_state", "user": "user_id", "date": "timestamp", "retDate": "return_date"}
    checkRentHistory(rentlog, keyMap)
    rentlog = list2dict(rentlog)
    updateMongoDB(db.rentLog, rentlog, log=True, debug = debug)

    print("="*80)
    print("Rent")
    updateMongoDB(db.rent, rents, debug = debug)

if __name__ == '__main__':
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


