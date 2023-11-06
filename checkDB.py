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

def checkDB(mongoDb):
    print("Check book DB")

    print("="*80)
    print("Book")
    books = mdb2dict(mongoDb.book)
    print(f"{len(books)} books")

    print("="*80)
    print("MARC")
    marcs = mdb2dict(mongoDb.marc)
    print(f"{len(marcs)} MARCs")

    print("="*80)
    print("Rent")
    rents = mdb2dict(mongoDb.rent)
    print(f"{len(rents)} rents")

    print("="*80)
    print("RentLog")
    rentLogs = mdb2dict(mongoDb.rentLog)
    print(f"{len(rentLogs)} rentLogs")

    print("="*80)
    print("Check DB")
    numDeleted = 0
    states = dict()
    for key in books:
        book = books[key]
        seqnum = book["seqnum"]
        if seqnum not in marcs:
            print(f"MARC for {key} is missing")
            print(book)
        if book['deleted'].lower() != marcs[seqnum]['DELETE_YN'].lower():
            print(f"Delete flag does not match in book and marc")
            print(book)
            print(marcs[seqnum])
        if book['deleted'] in {"Y", "y"}:
            numDeleted += 1
            if key in rents:
                print(f"Deleted book has a state")
                print(book)
                print(rents[key])
        else:
            if key[0:2] != "HK":
                print(f"Invalid ID {key}")
        if seqnum in rents:
            state = rents[seqnum]['state']
#            print(f"{key}: {state}")
            states[state] = states[state] + 1 if state in states else 1

    booksFromMarc = dict()
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
            if bytes(orgMarc, "UTF-8") != bytes(newMarc, "UTF-8"):
                mismatchCount += 1
            else:
                matchCount += 1
            book = marc.getBookInfo()
            barcode = book["BARCODE"]
            booksFromMarc[barcode] = book
        except Exception as e:
            print(f"Failed to decode MARC {e}")
            print(orgMarc)
            failCount += 1
    print(f"Same {matchCount} / Change {mismatchCount} / Fail {failCount} / Total {len(marcs)}")
    booksFromMarc = convertToMDB(booksFromMarc, "_id", sqlBookDict)

    for key in booksFromMarc:
        marcBook = booksFromMarc[key]
        mdbBook = books[key]
        for entry in marcBook:
            if entry in mdbBook and marcBook[entry] != mdbBook[entry]:
                print(f"Book {key} mismatch with MARC")
                print(mdbBook)
                print(marcBook)

    numValid = len(books) - numDeleted
    numAvail = numValid
    for state in states:
        numAvail -= states[state]

    print(f"Avaiable {numAvail} / Valld {numValid} / All {len(books)} / Deleted {numDeleted}")
    print(states)

    for key in rents:
        print(rents[key])
        break
    keyMap = {"idx": "_id", "book": "book_id", "state": "book_state", "user": "user_id", "date": "timestamp", "retDate": "return_date"}
    noReturn = checkRentHistory(dict2list(rentLogs), keyMap)
    count = 0
    for entry in noReturn:
        seqnum = books[entry]["seqnum"]
#        if entry not in rents:
        if seqnum not in rents:
            print(f"Book {entry} is not in rent list")
            count += 1
#        else:
#            print(f"Book {entry} is int state {rents[seqnum]['state']}")
    if count > 0:
        print(f"Mismatch cound {count}")
#    print(noReturn)
#    print(rents.keys())


if __name__ == '__main__':
    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    mongoDb = client.library

    checkDB(mongoDb)


