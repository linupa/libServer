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

    print("="*80)
    print("Book")
    updateMongoDB(db.book, books)

    print("="*80)
    print("MARC")
    updateMongoDB(db.marc, marcs)

    print("="*80)
    print("User")
    encryptUserInfo(users)
    updateMongoDB(db.user, users)

    print("="*80)
    print("Rent")
    updateMongoDB(db.rent, rents)

    print("="*80)
    print("RentHistory")
    updateMongoDB(db.rentLog, rentlog, log=True)

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library_test

    uploadDatabase(clib, db)


