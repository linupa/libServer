from pymongo import MongoClient
from config import Config
from clibrary import CLibrary
from dbUtil import *

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

def updateMongoDB(mdb, srcDB, log = False):
    mdbDict = mdb2dict(mdb)
    if "AB0354" in mdbDict:
        print(mdbDict["AB0354"])
    updates = compare(srcDB, mdbDict, log=log)
    updateCloud(updates, srcDB, mdb)

def uploadDatabase(clib, db):
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

    for key in rentlog:
        rent = rentlog[key]
        if rent["book_id"] == "HK10002064":
            print(rent)

    print("="*80)
    print("Book")
    updateMongoDB(db.book, books)

    print("="*80)
    print("MARC")
    updateMongoDB(db.marc, marcs)

    print("="*80)
    print("User")
    encryptUserInfo(users)
    print(users["AB0354"])
    print(db.user["AB0354"])

    updateMongoDB(db.user, users)

    print("="*80)
    print("RentHistory")
    rentlog = dict2list(rentlog)
    keyMap = {"idx": "_id", "book": "book_id", "state": "book_state", "user": "user_id", "date": "timestamp", "retDate": "return_date"}
    checkRentHistory(rentlog, keyMap)
    rentlog = list2dict(rentlog)
    for key in rentlog:
        if rentlog[key]["book_id"] == 'HK10002064':
            print(rentlog[key])
    updateMongoDB(db.rentLog, rentlog, log=True)

    print("="*80)
    print("Rent")
    updateMongoDB(db.rent, rents)

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library

    uploadDatabase(clib, db)


