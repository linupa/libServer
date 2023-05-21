from pymongo import MongoClient
from config import Config
from clibrary import CLibrary, dictToString
from dbUtil import *

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

def compareEntry(hist):
    return hist['REG_DATE']

def compareHistory(orig, modi):
    if len(orig) != len(modi):
        return False
    length = len(orig)
    for i in range(length):
        origItem = orig[i]
        modiItem = modi[i]
        if (origItem['BOOK_CODE'] != modiItem['BOOK_CODE'] or
            origItem['BOOK_STATE'] != modiItem['BOOK_STATE'] or
            origItem['USER_CODE'] != modiItem['USER_CODE'] or
            origItem['REG_DATE'] != modiItem['REG_DATE']):
            return False
    return True

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()

    rentHistory = clib.rentHistory.copy()
    print(len(rentHistory))
    rentHistory.sort(key=compareEntry)
    newList = list()
    for entry in rentHistory:
        length = len(newList)
        entry = entry.copy()
        count = 1
        dup = False
        while count < length and newList[-count]['REG_DATE'] == entry['REG_DATE']:
            lastItem = newList[-count]
            if (lastItem['BOOK_CODE'] == entry['BOOK_CODE'] and
                lastItem['BOOK_STATE'] == entry['BOOK_STATE'] and
                lastItem['USER_CODE'] == entry['USER_CODE']):
                print(f"Duplicate item {entry}")
                dup = True
                break
            count += 1
        if not dup:
            entry['SEQ'] = len(newList) + 1
            newList.append(entry)

    print(len(newList))

    if compareHistory(rentHistory, newList):
        print("No change")
        exit(0)

    print("Delete all entries")
    clib.db.UpdateQuery("delete from rental_history")

    for entry in newList:
        if "RETURN_DATA" in entry:
            del entry["RETURN_DATA"]
        label = dictToString(entry, labelOnly = True)
        value = dictToString(entry, valueOnly = True)
        queryStr = f"insert into rental_history ({label}) values ({value})"
        print(queryStr)
        clib.db.UpdateQuery(queryStr)


