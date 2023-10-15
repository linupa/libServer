from pymongo import MongoClient
from config import Config
from clibrary import CLibrary
from dbUtil import *

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

def updateDB(currDb, srcDb, dstDb, dbName, dbKey, log = False):
    updates = compare(srcDb, currDb, log=log)
    updateSQL(updates, srcDb, dstDb, dbName, dbKey)

def downloadBook(clib, db):
    print("="*80)
    print("Book")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict)
    updateDB(clib.books, books, clib, "book", "BARCODE")

    print("="*80)
    print("MARC")
    marcs = convertToSQL(db.marc, "SEQ", sqlMARCDict)
    updateDB(clib.marcs, marcs, clib, "marc", "SEQ")


def downloadDatabase(clib, db):
    print("Download database")

#    for key in books:
#        book = books[key]
#        if "MOD_DATE" not in book or len(book["MOD_DATE"]) == 0:
#            print(book)
#            book["MOD_DATE"] = book["REG_DATE"]
#            print(books[key])

    print("="*80)
    print("Book")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict)
    updateDB(clib.books, books, clib, "book", "BARCODE")

    print("="*80)
    print("MARC")
    marcs = convertToSQL(db.marc, "SEQ", sqlMARCDict)
    updateDB(clib.marcs, marcs, clib, "marc", "SEQ")

    print("="*80)
    print("User")
    users = convertToSQL(db.user, "USER_CODE", sqlUserDict)
    for key in users:
        user = users[key]
        if 'DELETE_YN' not in user:
            user['DELETE_YN'] = "N"
    updateDB(clib.users, users, clib, "users", "USER_CODE")

    print("="*80)
    print("Rent")
    rents = convertToSQL(db.rent, "BARCODE", sqlRentDict)
    for key in books:
        if key not in rents:
            rents[key] = {'SEQ': books[key]['SEQ'], 'BARCODE': key, 'STATS': 0, 'USERS': '', 'LENT_DATE': '', 'RETURN_DATE': '', 'RESERVE_USER': '', 'RESERVE_DATE': '', 'EXTEND_COUNT': 0, 'DELETE_YN': books[key]['DELETE_YN'], 'ATTACH': 'N', 'ATTACH_USER': ''}
    updateDB(clib.rents, rents, clib, "book_lent", "BARCODE")

    print("="*80)
    print("RentHistory")
    rentlog = convertToSQL(db.rentLog, "SEQ", sqlRentHistoryDict)
    for entry in clib.rentHistory:
        regDate = entry['REG_DATE']
        if len(regDate) == 18:
            print(regDate)
            regDate = regDate[0:11] + "0" + regDate[11:]
            print(regDate)
    updateDB(list2dict(clib.rentHistory, "SEQ"), rentlog, clib, "rental_history", "SEQ")

    checkUnique(rentlog, "SEQ")

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library
    print("Check")

    downloadDatabase(clib, db)
