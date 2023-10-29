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

def updateDB(currDb, srcDb, dstDb, dbName, dbKey, log = False):
    updates = compare(srcDb, currDb, log=log)
    updateSQL(updates, srcDb, dstDb, dbName, dbKey)
    return updates[0]

def downloadDatabase(clib, db):
    print("Download book database")

    print("="*80)
    print("Book")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict)
    newBookList = updateDB(clib.books, books, clib, "book", "BARCODE")

    newBooks = dict()
    print(newBookList)
    for bookId in newBookList:
        newBooks[bookId] = books[bookId]

    print("="*80)
    print("MARC")
    marcs = convertToSQL(db.marc, "SEQ", sqlMARCDict)
    updateDB(clib.marcs, marcs, clib, "marc", "SEQ")

    idx = 0
    for key in marcs:
        m = MARC(marcs[key]["MARC_DATA"])
        for entry in m.entries:
            if entry[0] == "049":
                item = entry[4]
                if item["l"][0:3] != "HK0":
                    break
                if "f" in item and item["f"] != "아동":
                    print(m.entries)
                    idx += 1

    print(idx)

    print("="*80)
    print("Rent")
    rents = dict()
    for bookId in newBooks:
        rents[bookId] = {'SEQ': books[bookId]['SEQ'], 'BARCODE': bookId, 'STATS': 0, 'USERS': '', 'LENT_DATE': '', 'RETURN_DATE': '', 'RESERVE_USER': '', 'RESERVE_DATE': '', 'EXTEND_COUNT': 0, 'DELETE_YN': books[bookId]['DELETE_YN'], 'ATTACH': 'N', 'ATTACH_USER': ''}
    for key in rents:
        print(rents[key])

    updateSQL([newBookList, list(), list()], rents, clib, "book_lent", "BARCODE")

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library

    downloadDatabase(clib, db)
