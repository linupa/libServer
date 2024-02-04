import os
from pymongo import MongoClient
from dbUtil import *
from marc import MARC
from authorCode import getAuthorCode
import subprocess

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

def checkDB(mongoDb):
    commit = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE)
    out, _ = commit.communicate()
    print("="*80)
    print(f"Commit: {out.decode().strip()}")

    print("="*80)
    print("Download library DB")

    print("="*80)
    print("Book")
    books = mdb2dict(mongoDb.book)
    print(f"{len(books)} books")

    print("="*80)
    print("MARC")
    marcs = mdb2dict(mongoDb.marc)
    print(f"{len(marcs)} MARCs")

    print("="*80)
    print("User")
    users = mdb2dict(mongoDb.user)
    print(f"{len(users)} users")

    print("="*80)
    print("Rent")
    rents = mdb2dict(mongoDb.rent)
    print(f"{len(rents)} rents")

    print("="*80)
    print("RentLog")
    rentLogs = mdb2dict(mongoDb.rentLog)
    print(f"{len(rentLogs)} rentLogs")

    numDeleted = 0
    stateHist = dict()
    seqNums = set()
    errorCount = 0
    print("="*80)
    print("Compare Book and MARC")
    for key in books:
        book = books[key]
        seqnum = book["seqnum"]
        if seqnum in seqNums:
            print(f"Duplicated seqNum {seqnum}")
            errorCount += 1
        seqNums.add(seqnum)
        if seqnum not in marcs:
            print(f"MARC for seq {key} is missing")
            print(book)
            errorCount += 1
        if book['deleted'].lower() != marcs[seqnum]['DELETE_YN'].lower():
            print(f"Delete flag does not match in book and marc")
            print(book)
            print(marcs[seqnum])
            errorCount += 1
        if book['deleted'].lower() == "y":
            numDeleted += 1
            if key in rents:
                print(f"Deleted book has a state")
                print(book)
                print(rents[key])
                errorCount += 1
        else:
            if key[0:2] != "HK":
                print(f"Invalid ID {key}")
                errorCount += 1
        if seqnum in rents:
            state = rents[seqnum]['state']
#            print(f"{key}: {state}")
            stateHist[state] = stateHist[state] + 1 if state in stateHist else 1

    print("="*80)
    print("Check Sequence numbers")
    print("Check MARC")
    for seqnum in marcs:
        if seqnum not in seqNums:
            print(f"Seq {seqnum} in MARC does not exist")
            errorCount += 1

    print("Check rents")
    for seqnum in rents:
        if seqnum not in seqNums:
            print(f"Seq {seqnum} in rent does not exist")
            errorCount += 1


    print("="*80)
    print("Check MARC data by regenerating MARC")
    booksFromMarc = dict()
    matchCount = 0
    mismatchCount = 0
    failCount = 0
    authorMismatch = 0
    for key in marcs:
        orgMarc = marcs[key]["MARC_DATA"]
        try:
            marc = MARC(orgMarc, debug=False)
            marc.decode()
            marc.check()
            newMarc = marc.encode()
            if bytes(orgMarc, "UTF-8") != bytes(newMarc, "UTF-8"):
                mismatchCount += 1
                errorCount += 1
            else:
                matchCount += 1
            book = marc.getBookInfo()
            barcode = book["BARCODE"]
            booksFromMarc[barcode] = book
            if "AUTHOR_CODE" in book and "AUTHOR" in book:
                authorCode = book["AUTHOR_CODE"]
                generatedAuthorCode = getAuthorCode(book["AUTHOR"].strip(), book["BOOKNAME"].strip())
            if authorCode != generatedAuthorCode:
#                print(f"{book['BARCODE']} Mismatch {authorCode} vs {generatedAuthorCode}")
                authorMismatch += 1
        except Exception as e:
            print(f"Failed to decode MARC {e}")
            print(orgMarc)
            print(book)
            failCount += 1
            errorCount += 1
    print(f"Same {matchCount} / Change {mismatchCount} / Fail {failCount} / Total {len(marcs)} // AuthorCode mismatch {authorMismatch}")
    booksFromMarc = convertToMDB(booksFromMarc, "_id", sqlBookDict)

    print("="*80)
    print("Compare Book and MARC")
    for key in booksFromMarc:
        marcBook = booksFromMarc[key]
        mdbBook = books[key]
        for entry in marcBook:
            if entry in mdbBook and marcBook[entry].strip() != mdbBook[entry].strip():
                print(f"Book {key} mismatch with MARC")
                print(mdbBook)
                print(marcBook)
                errorCount += 1

    numValid = len(books) - numDeleted
    numAvail = numValid
    for state in stateHist:
        numAvail -= stateHist[state]


    print("="*80)
    print("Check rent history")
    keyMap = {"idx": "_id", "book": "book_id", "state": "book_state", "user": "user_id", "date": "timestamp", "retDate": "return_date"}
    noReturn = checkRentHistory(dict2list(rentLogs), keyMap)

    print("="*80)
    print("Compare rent history and rent")
    count = 0
    for entry in noReturn:
        seqnum = books[entry]["seqnum"]
        userId = noReturn[entry]
#        if entry not in rents:
        if seqnum not in rents:
            print(f"Book {entry} is not in rent list")
            count += 1
            errorCount += 1
        elif userId != rents[seqnum]['user_id']:
            print(f"{entry} Renter {userId} is different from {rents[seqnum]['user_id']}")
            count += 1
            errorCount += 1

    print("="*80)
    print("Compare rent and book")
    bookPerSeq = dict()
    for bookId in books:
        seq = books[bookId]["seqnum"]
        bookPerSeq[seq] = books[bookId]

    for seqnum in rents:
        if seqnum not in bookPerSeq:
            print(f"{seqnum} not in book DB")
            errorCount += 1

    if count > 0:
        print(f"Mismatch cound {count}")

    print("="*80)
    print(f"Avaiable {numAvail} / Valld {numValid} / All {len(books)} / Deleted {numDeleted}")
    print(stateHist)

    print("="*80)
    print(f"Total error count {errorCount}")

    return errorCount

if __name__ == '__main__':
    # Open MongoDB
    if "GITHUB_ACTIONS" in os.environ:
        password = os.environ["MONGODB_PASSWORD"]
    else:
        from config import Config
        password = Config['password']
    connection = 'mongodb+srv://linupa:{}@hkmcclibrary.s59ur1w.mongodb.net/?retryWrites=true&w=majority'.format(password)
    client = MongoClient(connection)
    mongoDb = client.library

    checkDB(mongoDb)


