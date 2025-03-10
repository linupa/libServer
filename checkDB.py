import os
from pymongo import MongoClient
from dbUtil import *
from marc import MARC
from authorCode import getAuthorCode
import subprocess
from text import getText
import datetime
import argparse

def checkDuplicate(logs):
    lastEntity = None
    delEntity = list()
    for log in logs:

        if (lastEntity and log['timestamp'] == lastEntity['timestamp'] and
            log['user_id'] == lastEntity['user_id'] and
            log['book_id'] == lastEntity['book_id']):
            print(f"Duplicate entry {log}")
            print(f"                {lastEntity}")
            delEntity.append(log)
        else:
            lastEntity = log.copy()
    for entity in delEntity:
        logs.remove(entity)

def checkDB(mongoDb, fix= False):
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
    print("RentHistory")
    rentHistory = mdb2dict(mongoDb.rentHistory)
    print(f"{len(rentHistory)} rentHistory")

    print("="*80)
    print("RentLog")
    rentLog = mdb2dict(mongoDb.rentLog)
    print(f"{len(rentLog)} rentLog")

    print("="*80)
    print("Request")
    requests = mdb2dict(mongoDb.request)
    print(f"{len(requests)} requests")

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
            print(rents[seqnum])
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
        if key not in books:
            print(f"Book {key} does not exist ({booksFromMarc[key]})")
            errorCount += 1
            continue
        mdbBook = books[key]
        for entry in marcBook:
            # BOOK modification time and MARC time may not be the same
            if entry == "modification_date":
                continue
            if entry in mdbBook and marcBook[entry].strip() != mdbBook[entry].strip():
                print(f"Entry {entry} in Book {key} mismatch with MARC")
                print(mdbBook)
                print(marcBook)
                errorCount += 1

    numValid = len(books) - numDeleted
    numAvail = numValid
    for state in stateHist:
        numAvail -= stateHist[state]

    print("="*80)
    print("Check User")
    for key in users:
        user = users[key]
        userId = user['_id']
        if len(userId) < 2 or userId[0:2] not in {"AB", "AA"}:
            print("Invalid user id")
            print(user)

    print("="*80)
    print("Check RentHistory")
    keyMap = {"idx": "_id", "book": "book_id", "state": "book_state", "user": "user_id", "date": "timestamp", "retDate": "return_date"}
    if fix:
        noReturn = checkRentHistory(dict2list(rentHistory), keyMap, db=mongoDb.rentHistory, checkId = False)
    else:
        noReturn = checkRentHistory(dict2list(rentHistory), keyMap, checkId = False)

    print("="*80)
    print("Check RentLog")
    keyMap = {"idx": "_id", "book": "book_id", "state": "book_state", "user": "user_id", "date": "timestamp", "retDate": "return_date"}
    if fix:
        noReturn = checkRentHistory(dict2list(rentLog), keyMap, db=mongoDb.rentLog, checkId = True)
    else:
        noReturn = checkRentHistory(dict2list(rentLog), keyMap, checkId = True)

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
    for seqnum in rents:
        rent = rents[seqnum]
        if rent["state"] not in {1, "1", 3, "3"}:
            continue
        bookId = rent['book_id']
        if bookId not in noReturn:
            print(f"Book {bookId} is rented, but rentLog has no checkout")
            errorCount += 1

    if count > 0:
        print(f"Mismatch count {count}")

    print("="*80)
    print("Compare rent and book")
    for seqnum in rents:
        bookId = rents[seqnum]["book_id"]
        if bookId not in books:
            print(f"{bookId} not in book DB")
            print(rents[seqnum])
            errorCount += 1
            continue
        if seqnum != books[bookId]["seqnum"]:
            print(f"Rent {seqnum} does not match Book {bookId} seqnum {books[bookId]['seqnum']}")
            print(rents[seqnum])
            errorCount += 1
            continue

    print("="*80)
    print("Compare rent and user")
    overdueUsers = set()
    for seqnum in rents:
        rent = rents[seqnum]
        #  Check only rented or overdue cases
        if rent["state"] not in {1, "1", 3, "3"}:
            continue
        if "user_id" not in rent:
            print("Renter for {rent['book_id']} is missing")
            errorCount += 1
            continue
        bookId = rent["book_id"]
        userId = rent["user_id"]

        if userId not in users:
            print(f"{userId} is missing")
            print(rent)
            errorCount += 1
            continue
        user = users[userId]

        if user["deleted"] in {"y", "Y"}:
            print(f"{userId} is renting {bookId}, but ID is deleted")
            errorCount += 1

        if rent["state"] not in {3, "3"}:
            continue

        overdueUsers.add(userId)

        if user["state"] != 1:
            print(f"Book {bookId} is overdue, but user {userId} state is not overdue")
            errorCount += 1

    for userId in users:
        user = users[userId]

        # Check only only overdue user
        if user["state"] not in {1, "1"}:
            continue

        userId = user["_id"]
        if userId not in overdueUsers:
            print(f"{userId} is overdue but not in rent")
            errorCount += 1

    print("="*80)
    print("Compare rent history and rent log")
    rentHistoryList = dict2list(rentHistory)
    rentLogList = dict2list(rentLog)

    rentHistoryList.sort(key=logCompare)
    rentLogList.sort(key=logCompare)

    lastLogIdx = 0
    for log in rentLogList:
        if lastLogIdx < log['_id']:
            lastLogIdx = log['_id']
    print(f"Last log idx: {lastLogIdx}")

    print("=" * 80)
    print("Check RentHistory")
    checkDuplicate(rentHistoryList)
    checkRentHistory(rentHistoryList, keyMap, checkId = False)
    print(f"{len(rentHistoryList)} entries")
    print("=" * 80)
    print("Check RentLog")
    checkDuplicate(rentLogList)
    print(f"{len(rentLogList)} entries")
    rentLogList.sort(key=logCompareWithID)
    checkRentHistory(rentLogList, keyMap, checkId = True)
    rentLogList.sort(key=logCompare)

    idx1 = 0
    idx2 = 0
    newLogIdx = lastLogIdx + 1
    newRentHistory = list()
    while idx1 < len(rentHistoryList) and idx2 < len(rentLogList):
        rent1 = rentHistoryList[idx1]
        rent2 = rentLogList[idx2]
        logKey = rent2['_id']
        if rent1['timestamp'] == rent2['timestamp'] and rent1['book_id'] == rent2['book_id']:
            idx1 += 1
            idx2 += 1
            continue
        elif rent1['timestamp'] > rent2['timestamp'] or rent1['book_id'] > rent2['book_id']:
            print(f"Timestamp mismatch (rentLog has more)")
            print(rent1)
            print(rent2)
            if fix:
                newEntry = rent2.copy()
                del newEntry['_id']
                newRentHistory.append(newEntry)
                print(f"Append {newEntry} to rent history")
            idx2 += 1
        else:
            print(f"Timestamp mismatch (rentHistory has more)")
            print(rent1)
            print(rent2)
            if fix:
                newEntry = rent1.copy()
                newEntry['_id'] = newLogIdx
                rentLogList.append(newEntry)
                print(f"Append {newEntry} to rent log")
                newLogIdx += 1
            idx1 += 1

    if fix:
        print("Compare log histories again")
        rentHistoryList.sort(key=logCompare)
        rentLogList.sort(key=logCompare)
        idx1 = 0
        idx2 = 0
        newLogIdx = lastLogIdx + 1
        while idx1 < len(rentHistoryList) and idx2 < len(rentLogList):
            rent1 = rentHistoryList[idx1]
            rent2 = rentLogList[idx2]
            logKey = rent2['_id']
            if rent1['timestamp'] == rent2['timestamp']:
                idx1 += 1
                idx2 += 1
                continue
            elif rent1['timestamp'] > rent2['timestamp']:
                print(f"Timestamp mismatch (rentLog has more)")
                print(rent2)
                idx2 += 1
            else:
                print(f"Timestamp mismatch (rentHistory has more)")
                print(rent1)
                idx1 += 1
        checkRentHistory(rentLogList, keyMap, checkId = True)

        print("=" * 80)
        print("Rearrange log ids")
        rentLogList = renumberRentHistory(rentLogList)

        print("=" * 80)
        print("Check rent history again")
        checkRentHistory(rentLogList, keyMap, checkId = True)

        print("=" * 80)
        print("Update rent log")
        rentLog = list2dict(rentLogList)
        updates = compare(rentLog, mdb2dict(mongoDb.rentLog))
        updateCloud(updates, rentLog, mongoDb.rentLog)

        print("Update rent hitory")
        rentHistory = list2dict(rentHistoryList)
        if 24530 in rentHistory:
            print(f"From {rentHistory[24530]}")
        orgDb = mdb2dict(mongoDb.rentHistory)
        if 24530 in orgDb:
            print(f"To {orgDb[24530]}")
        updates = compare(rentHistory, mdb2dict(mongoDb.rentHistory), log = True)
#        updates[1] = list()
#        updates[2] = list()
        updateCloud(updates, rentHistory, mongoDb.rentHistory)
        updateCloud2([newRentHistory, list(), list()], mongoDb.rentHistory)

    print("="*80)
    print(f"Avaiable {numAvail} / Valld {numValid} / All {len(books)} / Deleted {numDeleted}")
    print(stateHist)

    print("="*80)
    print(f"Total error count {errorCount}")
    if errorCount > 0:
        raise

    print("="*80)
    print(f"Check requests")
    for key in requests:
        request = requests[key]
        print(request)
        if request["action"] != "extend":
            continue
        if request["state"] != "pending":
            continue
        bookId = request["book_id"]
        if bookId not in books:
            print(f"Unknown book ID: {bookId}")
            continue
        seq = books[bookId]["seqnum"]
        if seq not in rents:
            print(f"Unknown seq number: {seq}")
            for key in rents:
                rent = rents[key]
                if rent["book_id"] == bookId:
                    print(f"Found book in {rent}")
            continue
        rent = rents[seq]
        print(rent)
        if rent["book_id"] != bookId or rent["user_id"] != request["user_id"]:
            print(f"Rent info does not match {rent}")
        print(f"Extend due date {rent['return_date']} for {bookId}")
        dueDate = datetime.datetime.strptime(rent["return_date"], "%Y-%m-%d")
        print(dueDate)
        now = datetime.datetime.now()
        refDate = now if now > dueDate else dueDate
        newRetDate = timeToString(refDate + datetime.timedelta(days=21), True)
        print(f"New due date {newRetDate}")


    return [books, users, rents, rentHistory]

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--fix', action='store_true')

    args = parser.parse_args()
    # Open MongoDB
    if "GITHUB_ACTIONS" in os.environ:
        password = os.environ["MONGODB_PASSWORD"]
    else:
        from config import Config
        password = Config['password']
    connection = 'mongodb+srv://linupa:{}@hkmcclibrary.s59ur1w.mongodb.net/?retryWrites=true&w=majority'.format(password)
    print(connection)
    client = MongoClient(connection)
    mongoDb = client.library

    try:
        db = checkDB(mongoDb, args.fix)
    except Exception as e:
        print("checkDB failed")
        print(e)
        exit()

    books = db[0]
    rentHistory = db[3]

    rentPerYear = dict()
    for idx in rentHistory:
        rentLog = rentHistory[idx]
        if rentLog['book_state'] != 1:
            continue
        year = rentLog['timestamp'][0:4]
        if year not in rentPerYear:
            rentPerYear[year] = {"kid": 0, "rel": 0, "eng": 0, "other": 0, "total": 0}
        bookId = rentLog['book_id']
        if bookId[0:3] == "HK0" or bookId[0:3] == "HK9":
            rentPerYear[year]['kid'] += 1
        elif bookId[0:3] == "HK5":
            rentPerYear[year]['eng'] += 1
        else:
            book = books[bookId]
            if book['category'][0] == '2':
                rentPerYear[year]['rel'] += 1
            else:
                rentPerYear[year]['other'] += 1
        rentPerYear[year]['total'] += 1

    keys = ["kid", "rel", "eng", "other", "total"]

    item = [""]
    for k in keys:
        item.append(getText(k))
    print(",".join(item))
    for year in rentPerYear:
        item = [str(year)]
        for key in keys:
            item.append(str(rentPerYear[year][key]))
        print(",".join(item))

#    for i in books:
#        print(books[i])
#        break


