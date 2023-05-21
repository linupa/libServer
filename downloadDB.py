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
    books = convertToSQL(db.book, "BARCODE", sqlBookDict)
    updateDB(clib.books, books, clib, "book", "BARCODE")

def downloadDatabase(clib, db):
    print("Downlaod database")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict)
    for key in books:
        print(books[key])
        break
    users = convertToSQL(db.user, "USER_CODE", sqlUserDict)
    for key in users:
        print(users[key])
        break
    rents = convertToSQL(db.rent, "BARCODE", sqlRentDict)
    for key in rents:
        print(rents[key])
        break
    rentlog = convertToSQL(db.rentLog, "SEQ", sqlRentHistoryDict)
    for key in rentlog:
        print(rentlog[key])
        break

    print("="*80)
    print("Book")
    updateDB(clib.books, books, clib, "book", "BARCODE")

    print("="*80)
    print("User")
    updateDB(clib.users, users, clib, "users", "USER_CODE")

    print("="*80)
    print("Rent")
    for key in books:
        if key not in rents:
            rents[key] = {'SEQ': books[key]['SEQ'], 'BARCODE': key, 'STATS': 0, 'USERS': '', 'LENT_DATE': '', 'RETURN_DATE': '', 'RESERVE_USER': '', 'RESERVE_DATE': '', 'EXTEND_COUNT': 0, 'DELETE_YN': books[key]['DELETE_YN'], 'ATTACH': 'N', 'ATTACH_USER': ''}
    updateDB(clib.rents, rents, clib, "book_lent", "BARCODE")

    print("="*80)
    print("RentHistory")
    updateDB(list2dict(clib.rentHistory, "SEQ"), rentlog, clib, "rental_history", "SEQ")

    checkUnique(rentlog, "SEQ")

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library_test
    print("Check")

    downloadDatabase(clib, db)
