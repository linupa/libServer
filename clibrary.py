#!/usr/python3

import sys
from clibdb import CLibDB
import datetime
import base64
import re
from dbUtil import *

USER_NORMAL  = 0
USER_OVERDUE = 1
USER_BLOCKED = 2

BOOK_AVAILABLE = 0
BOOK_RENTED    = 1
BOOK_RESERVED  = 2
BOOK_OVERDUE   = 3
BOOK_LOST      = 4
BOOK_DAMAGED   = 5
BOOK_GIVEN     = 6
BOOK_NOT_AVAIL = 7
BOOK_DELETED   = 8

MAX_EXTEND = 3
MAX_RENTAL = 5
RENT_PERIOD = 22

def checkRentHistory(rentlog):
    print("Check rent history validity...")
    rentLogList = list()
    for i in range(len(rentlog)):
        logCopy = rentlog[i].copy()
        logCopy['IDX'] = i
        rentLogList.append(logCopy)

    numCheckout = 0
    numReturn = 0
    noReturn = set()
    for i in range(len(rentLogList)):
        log = rentLogList[i]
        idx = log['IDX']
        bookId = log['BOOK_CODE']
        state = log['BOOK_STATE']
        timestamp = log['REG_DATE']
        user = log['USER_CODE']
#        if bookId == 'HK10000073':
#            print(f"{idx} Returned {rentlog[idx]} {type(state)} {log['SEQ']} ~ {log2['SEQ']}")
        # Skip reservation
        if state in {2, '2'}:
            continue
        if state in {1, '1'}:
            returned = False
            otherRent = False
            numCheckout += 1
            for j in range(i + 1, len(rentLogList)):
                log2 = rentLogList[j]
                if bookId != log2['BOOK_CODE']:
                    continue
                if log2['BOOK_STATE'] in {0, '0'} and user == log2['USER_CODE']:
                    returned = True
                    break
                if not otherRent and log2['BOOK_STATE'] in {1, '1'} and user != log2['USER_CODE']:
                    otherRent = True
                    otherRentDate = log2['REG_DATE']
            if returned:
                rentlog[idx]['RETURN_DATA'] = log2['REG_DATE']
            elif otherRent:
                rentlog[idx]['RETURN_DAT'] = otherRentDate
            else:
                noReturn.add(bookId)
        if state in {0, '0'}:
            numReturn += 1
#        if log['SEQ'] == 352:
#            print(f"{idx} Returned {rentlog[idx]} {type(state)} {log['SEQ']} ~ {log2['SEQ']}")
    print(f"Checkout: {numCheckout}, Return: {numReturn}, NoReturn: {len(noReturn)}")

# BOOK
#    ['SEQ', 'BARCODE', 'RFID', 'BOOKNAME', 'BOOKNUM', 'AUTHOR', 'TOTAL_NAME', 'CATEGORY', 'AUTHOR_CODE', 'CLAIMNUM', 'COPYNUM', 'EX_CATE', 'ISBN', 'PUBLISH', 'ATTACH', 'CLAIM', 'LOCATION', 'BOOKIN', 'REG_DATE', 'MOD_DATE', 'DELETE_YN']

# RENT
#    ['SEQ', 'BARCODE', 'STATS', 'USERS', 'LENT_DATE', 'RETURN_DATE', 'RESERVE_USER', 'RESERVE_DATE', 'EXTEND_COUNT', 'DELETE_YN', 'ATTACH', 'ATTACH_USER']

# RENT LOG
#    ['SEQ', 'BOOK_CODE', 'BOOK_STATE', 'USER_CODE', 'REG_DATE']

# USER
#    ['SEQ', 'USER_CODE', 'USER_NAME', 'PHONE_NUMBER', 'ADDRESS', 'EMAIL', 'USER_LEVEL', 'USER_STATE', 'NOTICE', 'USER_IMAGE', 'DISABLE_DATE', 'DELAY_DAY', 'DELAY_CHARGE', 'REG_DATE', 'MOD_DATE', 'DELETE_YN']

class CLibrary:
    def __init__(self):
        self.db = CLibDB()
        tables = ('BOOK', 'BOOK_LENT', 'RENTAL_HISTORY', 'USERS', 'MARC', 'MARC_TAG'  )

        data = dict()
        for tableName in tables:
            data[tableName] = list()
            table = data[tableName]

            query = f"select * from information_schema.columns where table_name='{tableName}'"
            labels = self.db.RunQuery(query)

            label = list()
            for j in range(len(labels)):
                label.append(labels[j][3])
            print(label)

            query = f"select * from {tableName}"
            items = self.db.RunQuery(query)
#            print(items)
            for item in items:
                entry = dict()
                for j in range(len(labels)):
                    entry[label[j]] = item[j]

                table.append(entry)
            print(tableName)
            print(len(table))
#        print(data)
        self.books = dict()
        numBook = 0
        for book in data['BOOK']:
            barcode = book['BARCODE']
            self.books[barcode] = book
            if book['DELETE_YN'] != 'Y':
                numBook += 1
        print(f"{numBook} books")

        count = 0
        self.marcs = dict()
        numMARC = 0
        for marc in data['MARC']:
            seq = marc['SEQ']
            self.marcs[seq] = marc
            if marc['DELETE_YN'] != 'Y':
                numMARC += 1

        print(f"{numMARC} MARCs")

        self.users = dict()
        numUser = 0
        for user in data['USERS']:
            usercode = user['USER_CODE']
            self.users[usercode] = user
            if user['DELETE_YN'] != 'Y':
                numUser += 1
        print(f"{numUser} users")

        self.rents = dict();
        for rent in data['BOOK_LENT']:
            barcode = rent['BARCODE']
            self.rents[barcode] = rent
        print(f"{len(self.rents)} rents")

        self.rentHistory = data['RENTAL_HISTORY'].copy()

        self.rentHistory.sort(key=lambda e : logKey(e,"REG_DATE"))

        checkUnique(self.rentHistory, key="SEQ")
        print(f"Max rent history seq {self.getMaxRentLog()}")

        self.updateDatabase()

#        print(self.books)
#        print(self.users)
#        print(self.rents)
#        print(self.rentHistory)

#        queryStr = f"update book_lent set STATS='2', USERS='0001',LENT_DATE='2003-03-29 10:10:10', RETURN_DATE='2023-04-27' where BARCODE='A000'"
#        self.db.UpdateQuery(queryStr)
#        datetime.datetime.strptime(ns, '%Y-%m-%d %H:%M:%S')

    def close(self):
        print("Close DB")
        self.db.close()

    def getNewUserId(self):
        idList = list(self.users.keys())
        if len(idList) > 0:
            idList.sort()

            lastId = idList[-1]
            lastNumber = re.findall(r'[0-9]+', lastId)[-1]
            numIndex = lastId.rfind(lastNumber)
            numLen = len(lastNumber)
            prefix = lastId[0:numIndex]
            lastIdx = int(lastNumber)

            newId = prefix + str(lastIdx + 1).zfill(numLen)
            print(newId)
            return newId
        else:
            return ""
    def getMaxUserSeq(self):
        maxSeq = 0
        for key in self.users:
            if 'SEQ' not in self.users[key]:
                print(self.users[key])
                continue
            seq = self.users[key]['SEQ']
            if maxSeq < seq:
                maxSeq = seq

        return maxSeq

    def getMaxRentLog(self):
        maxSeq = 0
        for entry in self.rentHistory:
            seqNum = int(entry["SEQ"])
            if seqNum > 100000000000:
                continue
            if maxSeq < seqNum:
                maxSeq = seqNum

        return maxSeq


    def getDueDate(self):
        now = datetime.datetime.now()
        retDate = now + datetime.timedelta(days=RENT_PERIOD)
        return timeToString(retDate, dateOnly=True)

    def updateDatabase(self):
        print("Update database");

        for key in self.books:
            book  = self.books[key]
            book['_STATE'] = BOOK_AVAILABLE

        for key in self.users:
            self.users[key]["_RENT"] = list()

        for key in self.rents:
            rent = self.rents[key]
#            print(rent)
            barcode = rent['BARCODE']
            userId = rent['USERS']
            self.rents[barcode] = rent
            if userId in self.users:
                self.users[userId]['_RENT'].append(barcode)
            self.books[barcode]['_STATE'] = rent['STATS'];
            self.books[barcode]['_RENT'] = self.rents[barcode]['LENT_DATE']
            self.books[barcode]['_RETURN'] = self.rents[barcode]['RETURN_DATE']
            self.books[barcode]['_EXTEND_COUNT'] = self.rents[barcode]['EXTEND_COUNT']

        overdueUser = set()
        for key in self.rents:
            rent = self.rents[key]
            if rent['STATS'] == BOOK_OVERDUE:
#                print(key)
                returnDate = stringToTime(rent['RETURN_DATE'])
                now = datetime.datetime.now()
#                print(timeToString(returnDate))
                if now > returnDate:
                    overdueUser.add(rent['USERS'])
                else:
                    rent['STATS'] = BOOK_RENTED
                    self.updateRent(rent)

            elif rent['STATS'] == BOOK_RENTED:
#                print(key)
                user = rent['USERS']
                returnDate = stringToTime(rent['RETURN_DATE'])
                now = datetime.datetime.now()
#                print(timeToString(returnDate, dateOnly=True))
                if now > returnDate:
                    print(f"Book {key} became overdue")
                    rent['STATS'] = BOOK_OVERDUE
                    self.updateRent(rent)
                    overdueUser.add(rent['USERS'])

        print(f"Overdue users: {overdueUser}")
        for key in self.users:
            user = self.users[key]
            modified = False
            if user['USER_STATE'] == USER_NORMAL and key in overdueUser:
                user['USER_STATE'] = USER_OVERDUE
                modified = True
            elif user['USER_STATE'] != USER_NORMAL and key not in overdueUser:
                user['USER_STATE'] = USER_NORMAL
                modified = True
            if modified:
                self.updateUser(key)

        checkRentHistory(self.rentHistory)


    def updateUserState(self, userKey, state):
        print("Update user state");
        user = self.users[userKey]
        user['USER_STATE'] = state
        self.updateUser(userKey)

        return "SUCCESS"

    def updateUser(self, userKey):
        user = self.users[userKey].copy()
        user.pop('SEQ')
        user.pop('USER_CODE')
        user.pop('USER_NAME')
        user['MOD_DATE'] = timeToString(datetime.datetime.now())
        value = dictToString(user)
        queryStr = f"update users set {value} where USER_CODE='{userKey}'"
        print(queryStr)
        self.db.UpdateQuery(queryStr)

    def updateRent(self, rent):
        book = rent['BARCODE']
        rent = rent.copy()
        rent.pop('SEQ')
        rent.pop('BARCODE')
#        rent.pop('RESERVE_USER')
#        rent.pop('RESERVE_DATE')
#        rent.pop('EXTEND_COUNT')
        rent.pop('ATTACH')
        rent.pop('ATTACH_USER')
#        rent.pop('DELETE_YN')
        value = dictToString(rent)
        queryStr = f"update book_lent set {value} where BARCODE='{book}'"
#        queryStr = f"update book_lent set STATS='1', USERS='0001',LENT_DATE='2003-04-29 10:10:10', RETURN_DATE='2023-05-09' where BARCODE='A001'"
#        queryStr = "update book_lent set STATS='1', USERS='0003', LENT_DATE='2023-04-29 02:49:30', RETURN_DATE='2023-05-20'  where BARCODE='A000'"
        print(queryStr)
        self.db.UpdateQuery(queryStr)

    def updateUserInfo(self, info):
        print(info)

        userKey = info['USER_CODE']
        info['MOD_DATE'] = timeToString(datetime.datetime.now())

        if len(userKey) > 0:
            print(f"Update account {userKey}")
            if userKey not in self.users:
                return False

            self.users[userKey].update(info)

            user = self.users[userKey].copy()
            user.pop('USER_CODE')
            label = dictToString2(user)
            value = dictToString2(user, valueOnly = True)
            queryStr = f"update users set {label} where USER_CODE='{userKey}'"
        else:
            print(f"Create a new account")
            userKey = self.getNewUserId()
            maxSeq = self.getMaxUserSeq()

            newInfo = dict()
            newInfo['SEQ'] = maxSeq
            newInfo['USER_CODE'] = ""
            newInfo['USER_NAME'] = ""
            newInfo['PHONE_NUMBER'] = ""
            newInfo['ADDRESS'] = ""
            newInfo['EMAIL'] = ""
            newInfo['USER_LEVEL'] = ""
            newInfo['USER_STATE'] = 0
            newInfo['NOTICE'] = ""
            newInfo['USER_IMAGE'] = ""
            newInfo['DISABLE_DATE'] = ""
            newInfo['DELAY_DAY'] = ""
            newInfo['DELAY_CHARGE'] = ""
            newInfo['DELETE_YN'] = "N"
            newInfo['_RENT'] = []

            if 'USER_NAME' not in info or len(info['USER_NAME']) == 0 or 'USER_LEVEL' not in info or int(info['USER_LEVEL']) < 0:
               return False

            newInfo.update(info)
            newInfo['USER_CODE'] = userKey
            newInfo['MOD_DATE'] = info['MOD_DATE']
            newInfo['REG_DATE'] = info['MOD_DATE']
            newInfo['_RENT'] = []
            newInfo['SEQ'] = maxSeq + 1
            self.users[userKey] = newInfo

            user = self.users[userKey].copy()
            label = dictToString(user, labelOnly = True)
            value = dictToString2(user, valueOnly = True)
            queryStr = f"insert into users ({label}) values ({','.join(['?'] * len(value))})"

        print(queryStr)
        print(value)
        try:
            self.db.UpdateQueryWithValue(queryStr, value)
        except Exception as e:
            print(e)
            return False

        return True

    def addHistory(self, rent, user):
        now = datetime.datetime.now()
        history = dict()
        history['SEQ'] = str(self.getMaxRentLog() + 1)
        history['BOOK_CODE'] = rent['BARCODE']
        history['BOOK_STATE'] = rent['STATS']
        history['USER_CODE'] = user
        history['REG_DATE'] = timeToString(now)
        self.rentHistory.append(history)
        print(history)
        label = dictToString(history, labelOnly = True)
        value = dictToString(history, valueOnly = True)
        queryStr = f"insert into rental_history ({label}) values ({value})"
        print(queryStr)
        self.db.UpdateQuery(queryStr)

    def findUser(self, userId):
        if userId in self.users:
            return self.users[userId]
        else:
            return None

    def findUsers(self, userText):
        ret = list()
        keyword64 = userText
        print(keyword64)
        keywordBin = base64.b64decode(keyword64)
        print(keywordBin)
        keyword = keywordBin.decode('UTF8')
        print(f"Decoded {userText} => {keyword}")

        print(f"Search {len(self.users)} users")
        for key in self.users:
            user = self.users[key]
#            print(user['USER_NAME'])
            if user['DELETE_YN'] == "Y":
                continue
            if user['USER_NAME'].find(keyword) >= 0 or key == keyword:
                ret.append(user)
            if len(ret) >= 100:
                break

        ret.sort(key= lambda user1: user1['USER_NAME'])

        return ret

    def findBook(self, bookId = None, userId = None, match = True):
        print(f"Find Book {userId}")
        if match == 'false':
            match = False
        elif match == 'true':
            match = True
        print(f"Find {match}")
        ret = list()
        if match:
            if bookId:
                print(bookId)
                if bookId in self.books:
                    return self.books[bookId]
            elif userId:
                print(f"UserID: {userId}")
                for key in self.rents:
                    rent = self.rents[key]
                    if userId != "*" and userId != rent['USERS']:
                        continue
                    if rent['STATS'] != 1 and rent['STATS'] != 3:
                        continue
                    book = self.books[key].copy()
                    book['BARCODE'] = key
                    book['STATS'] = rent['STATS']
                    book['LENT_DATE'] = rent['LENT_DATE']
                    book['RETURN_DATE'] = rent['RETURN_DATE']
                    book['USER'] = rent['USERS']
                    book['EXTEND_COUNT'] = rent['EXTEND_COUNT']
                    if rent['USERS'] in self.users:
                        book['USER_NAME'] = self.users[rent['USERS']]['USER_NAME']

                    ret.append(book)
        else:
            keyword64 = bookId
            print(keyword64)
            keywordBin = base64.b64decode(keyword64)
            print(keywordBin)
            keyword = keywordBin.decode('UTF8')
            print(f"Decoded {bookId}")
            if keyword in self.books:
                return list([self.books[keyword]])
            for key in self.books:
                book = self.books[key]
                if book['DELETE_YN'] == 'Y':
                    continue
                if book['BOOKNAME'].find(keyword) >= 0:
                    ret.append(book)
                if len(ret) >= 100:
                    break
        return ret

    def getHistory(self, period):
        ret = list()
        if len(period) == 0:
            return ret
        print(period)
        for log in self.rentHistory:
#            log = self.rentHistory[key]
            if log['BOOK_STATE'] != 1 or 'RETURN_DATA' not in log:
                continue
#            if period not in log['REG_DATE']:
#                continue
            if log['REG_DATE'].find(period) != 0:
                continue
            print(log)
            entry = dict()
            bookId = log['BOOK_CODE']
            entry.update(self.books[bookId])
            entry['RENT_DATE'] = log['REG_DATE']
            entry['RETURN_DATE'] = log['RETURN_DATA']
            userId = log['USER_CODE']
            entry['USER'] = userId
            if userId in self.users:
                entry['USER_NAME'] = self.users[userId]['USER_NAME']
            else:
                entry['USER_NAME'] = ""

            ret.append(entry)

        return ret

    def setBookInfo(self, bookKey, state):
        print(f"Set book info {bookKey} {state}")
        if bookKey not in self.books:
            return "INVALID_BOOK"

        if self.rents[bookKey]['STATS'] in {BOOK_RENTED, BOOK_OVERDUE}:
            self.returnBook(bookKey)

        self.rents[bookKey]['STATS'] = state
        self.rents[bookKey]['USERS'] = ""
        self.rents[bookKey]['LENT_DATE'] = ""
        self.rents[bookKey]['RETURN_DATE'] = ""
        self.rents[bookKey]['EXTEND_COUNT'] = 0
        self.rents[bookKey]['RESERVE_USER'] = ""
        self.rents[bookKey]['RESERVE_DATE'] = ""

        self.updateRent(self.rents[bookKey])

        self.addHistory(self.rents[bookKey], "")

        self.updateDatabase()

        return "SUCCESS"

    def checkOutBook(self, bookKey, userKey, admin = False):
        print(f"{userKey} rents book {bookKey}")
        if bookKey not in self.books:
            return "INVALID_BOOK"

        if userKey not in self.users:
            return "INVALID_USER"

        if self.rents[bookKey]['STATS'] != BOOK_AVAILABLE:
            return "NOT_AVAILABLE"

#        now = datetime.datetime.now() - datetime.timedelta(days=30)
        now = datetime.datetime.now()
        rentCount = 0
        if not admin:
            for key in self.rents:
                rent = self.rents[key]
                if rent['USERS'] != userKey:
                    continue
                if rent['STATS'] == BOOK_OVERDUE:
                    return "OVERDUE"

                rentCount += 1

        if rentCount >= MAX_RENTAL:
            return "MAX_RENTAL"

        retDate = now + datetime.timedelta(days=RENT_PERIOD)
        self.rents[bookKey]['STATS'] = BOOK_RENTED
        self.rents[bookKey]['USERS'] = userKey
        self.rents[bookKey]['LENT_DATE'] = timeToString(now)
        self.rents[bookKey]['RETURN_DATE'] = timeToString(retDate, dateOnly=True)
        self.rents[bookKey]['RESERVE_USER'] = ""
        self.rents[bookKey]['RESERVE_DATE'] = ""
        self.rents[bookKey]['EXTEND_COUNT'] = 0
        self.rents[bookKey]['ATTACH'] = "N"
        self.rents[bookKey]['ATTACH_USER'] = ""

        print(self.rents[bookKey])
        self.updateRent(self.rents[bookKey])

        self.addHistory(self.rents[bookKey], userKey)

        self.updateDatabase()

        return "SUCCESS"

    def extendBook(self, bookKey, admin = False):
        print(f"extend book {bookKey}")
        if bookKey not in self.books:
            return "INVALID_BOOK"

        if self.rents[bookKey]['STATS'] not in {BOOK_RENTED, BOOK_OVERDUE}:
            return "NOT_AVAILABLE"

#        now = datetime.datetime.now() - datetime.timedelta(days=30)
        now = datetime.datetime.now()
        if not admin:
            if self.rents[bookKey]['EXTEND_COUNT'] >= MAX_EXTEND:
                return "MAX_DETEND";

            for key in self.rents:
                rent = self.rents[key]
                if rent['STATS'] == BOOK_OVERDUE:
                    return "OVERDUE"


        newRetDate = timeToString(now + datetime.timedelta(days=RENT_PERIOD), True)
        retDate = self.rents[bookKey]['RETURN_DATE']

        print(f"Compare {retDate} and {newRetDate}")
        if retDate >= newRetDate:
            return "NOT_AVAILABLE"

        self.rents[bookKey]['STATS'] = BOOK_RENTED
        self.rents[bookKey]['RETURN_DATE'] = newRetDate
        self.rents[bookKey]['RESERVE_USER'] = ""
        self.rents[bookKey]['RESERVE_DATE'] = ""
        self.rents[bookKey]['EXTEND_COUNT'] = self.rents[bookKey]['EXTEND_COUNT'] + 1

        print(self.rents[bookKey])
        self.updateRent(self.rents[bookKey])

#        self.addHistory(self.rents[bookKey], userKey)

        self.updateDatabase()

        return "SUCCESS"

    def returnBook(self, bookKey):
        print(f"Return {bookKey}")
        print(self.books[bookKey])
        print(self.rents[bookKey])

        if bookKey not in self.books:
            return "INVALID_BOOK"

        if self.rents[bookKey]['STATS'] not in {1, 3}:
            return "NOT_RENTED"

        user = self.rents[bookKey]['USERS']

        self.rents[bookKey]['STATS'] = BOOK_AVAILABLE
        self.rents[bookKey]['USERS'] = ""
        self.rents[bookKey]['LENT_DATE'] = ""
        self.rents[bookKey]['EXTEND_COUNT'] = 0
        self.rents[bookKey]['RETURN_DATE'] = ""
        self.rents[bookKey]['RESERVE_USER'] = ""
        self.rents[bookKey]['RESERVE_DATE'] = ""

        self.updateRent(self.rents[bookKey])

        self.addHistory(self.rents[bookKey], user)

        self.updateDatabase()

        return "SUCCESS"


