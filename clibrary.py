#!/usr/python3

import sys
from clibdb import CLibDB
import datetime
import base64

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

MAX_RENTAL = 5
RENT_PERIOD = 21

def timeToString(t, dateOnly = False):
    if dateOnly:
        return t.strftime("%Y-%m-%d")
    else:
        return t.strftime("%Y-%m-%d %H:%M:%S")

def stringToTime(s):
    if s.find(":") > 0:
        form = '%Y-%m-%d %H:%M:%S'
    else:
        form = '%Y-%m-%d'
    return datetime.datetime.strptime(s, form)

def dictToString(d, labelOnly = False, valueOnly = False):
    l = list()
    for key in d:
#        if isinstance(d[key], int):
#            value = str(d[key])
#        else:
        if key[0] == '_':
            continue
        value = f"'{d[key]}'"

        if labelOnly:
            l.append(f"{key}")
        elif valueOnly:
            l.append(value)
        else:
            l.append(f"{key}={value}")
    return ", ".join(l)

class CLibrary:
    def __init__(self):
        self.db = CLibDB()
        tables = ('BOOK', 'BOOK_LENT', 'RENTAL_HISTORY', 'USERS'  )

        data = dict()
        for tableName in tables:
            data[tableName] = list()
            table = data[tableName]

            query = f"select * from information_schema.columns where table_name='{tableName}'"
            labels = self.db.RunQuery(query)

#            print(labels)
            query = f"select * from {tableName}"
            items = self.db.RunQuery(query)
#            print(items)
            for item in items:
                entry = dict()
                for j in range(len(labels)):
                    entry[labels[j][3]] = item[j]

                table.append(entry)
#            print(tableName)
#            print(table)
#        print(data)
        self.books = dict()
        for book in data['BOOK']:
            barcode = book['BARCODE']
            self.books[barcode] = book

        self.users = dict()
        for user in data['USERS']:
            usercode = user['USER_CODE']
            self.users[usercode] = user

        self.rents = dict();
        for rent in data['BOOK_LENT']:
            barcode = rent['BARCODE']
            self.rents[barcode] = rent

        self.rentHistory = data['RENTAL_HISTORY'].copy()

        self.updateDatabase()

#        print(self.books)
#        print(self.users)
#        print(self.rents)
#        print(self.rentHistory)

#        queryStr = f"update book_lent set STATS='2', USERS='0001',LENT_DATE='2003-03-29 10:10:10', RETURN_DATE='2023-04-27' where BARCODE='A000'"
#        self.db.UpdateQuery(queryStr)
#        datetime.datetime.strptime(ns, '%Y-%m-%d %H:%M:%S')

    def close(self):
        self.db.close()

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

    def addHistory(self, rent, user):
        now = datetime.datetime.now()
        history = dict()
        history['SEQ'] = len(self.rentHistory)
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

    def findBook(self, bookId, match = True):
        if match == 'false':
            match = False
        elif match == 'true':
            match = True
        if match:
            print(bookId)
            if bookId in self.books:
                return self.books[bookId]
        else:
            ret = list()
            keyword64 = bookId
            print(keyword64)
            keywordBin = base64.b64decode(keyword64)
            print(keywordBin)
            keyword = keywordBin.decode('UTF8')
            print(f"Decoded {bookId}")
            for key in self.books:
                book = self.books[key]
                if book['BOOKNAME'].find(keyword) >= 0:
                    ret.append(book)
                if len(ret) >= 100:
                    break
            return ret
        return None

    def checkOutBook(self, bookKey, userKey):
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

        print(self.rents[bookKey])
        self.updateRent(self.rents[bookKey])

        self.addHistory(self.rents[bookKey], userKey)

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
        self.rents[bookKey]['RETURN_DATE'] = ""
        self.rents[bookKey]['RESERVE_USER'] = ""
        self.rents[bookKey]['RESERVE_DATE'] = ""

        self.updateRent(self.rents[bookKey])

        self.addHistory(self.rents[bookKey], user)

        self.updateDatabase()

        return "SUCCESS"


