from pymongo import MongoClient
from config import Config
from clibrary import CLibrary
from dbUtil import *

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

def uploadDatabase(clib, mongoDb):
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
    mdbDict = mdb2dict(mongoDb.book)
    print(f"Local {len(books)}, Remote {len(mdbDict)}")
    if "AB0354" in mdbDict:
        print(mdbDict["AB0354"])
    updates = compare(books, mdbDict, log=False)
    #updateCloud(updates, srcDB, mongoDb.book)
    lastSeq = 0
    for key in mdbDict:
        mdb = mdbDict[key]
        if mdb['seqnum'] > lastSeq:
            lastSeq = mdb['seqnum']
    lastSeq += 1

    print(f"Max SEQ in cloud: {lastSeq}")

    newBookIds = updates[0]

    newMARCIds = list()
    newBooks = dict()
    newMARCs = dict()

    for key in newBookIds:
        newBooks[key] = books[key].copy()
        seq = books[key]['seqnum']
        newBooks[key]["seqnum"] = lastSeq
        newMARCs[lastSeq] = marcs[seq].copy()
        newMARCs[lastSeq]["_id"] = lastSeq
        newMARCIds.append(lastSeq)
        print(newBooks[key])
        print(newMARCs[lastSeq])
        lastSeq += 1

    print("=" * 80)
    print(newBookIds)
    print(newMARCIds)

    mdbBook = mdb2dict(mongoDb.book)
    mdbMARC = mdb2dict(mongoDb.marc)

    for key in newBooks:
        if key in mdbBook:
            print(f"Duplicated ID:")
            print(f" {mdbBook[key]}")
            print(f" {newBooks[key]}")
        else:
            mdbBook[key] = newBooks[key]
        seq = newBooks[key]["seqnum"]
        if seq in mdbMARC:
            print(f"Duplicated seq:")
            print(f" {mdbMARC[seq]}")
            print(f" {newMARCs[seq]}")
        else:
            mdbMARC[seq] = newMARCs[seq]


    mdbList = dict2list(mdbDict)
    mdbList.sort(key=lambda entry : entry["seqnum"] )
#    for i in range(-100, 0):
#        print(mdbList[i])

#    print(newMARCIds)
#    print(newMARCs)
#    delBook = ['HK00006647', 'HK00006648', 'HK00006649', 'HK00006650', 'HK10004732', 'HK10004923', 'HK10004924', 'HK10004925', 'HK10004927', 'HK10004928', 'HK10004929', 'HK10004930', 'HK10004931', 'HK50001293', 'HK10004932', 'HK10004933', 'HK10004934', 'HK10004935', 'HK10004936', 'HK10004937', 'HK10004938', 'HK10004939', 'HK10004940', 'HK10004941', 'HK10004942', 'HK10004943', 'HK10004944', 'HK10004945', 'HK10004946']
#    updateCloud([list(), list(), delBook], newBooks, mongoDb.book)
    updateCloud([newBookIds, list(), list()], newBooks, mongoDb.book)
    updateCloud([newMARCIds, list(), list()], newMARCs, mongoDb.marc)

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()
    print("Got clib")

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    mongoDb = client.library_test

    uploadDatabase(clib, mongoDb)


