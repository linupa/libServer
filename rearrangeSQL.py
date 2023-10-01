from pymongo import MongoClient
from config import Config
from clibrary import CLibrary, dictToString
from dbUtil import *

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

def compareEntry(hist):
    return hist['REG_DATE'] + " " + hist["BOOK_CODE"] + " " + hist["USER_CODE"]

def compareHistory(orig, modi):
    if len(orig) != len(modi):
        return False
    length = len(orig)
    print(length)
    for i in range(length):
        origItem = orig[i]
        modiItem = modi[i]
        if ( origItem['SEQ'] != modiItem['SEQ'] or
            origItem['BOOK_CODE'] != modiItem['BOOK_CODE'] or
            origItem['BOOK_STATE'] != modiItem['BOOK_STATE'] or
            origItem['USER_CODE'] != modiItem['USER_CODE'] or
            origItem['REG_DATE'] != modiItem['REG_DATE']):
            print(origItem)
            print(modiItem)
            return False
    return True

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()

    print("="*80)
    print("  Rearrange SQL DB")
    print("="*80)


    rentHistory = clib.rentHistory.copy()
    print(f"{len(rentHistory)}")

    for entry in rentHistory:
        if entry["BOOK_CODE"] == "HK10002064":
            print(entry)

    keyMap = {"idx": "IDX", "book": "BOOK_CODE", "state": "BOOK_STATE", "user": "USER_CODE", "date": "REG_DATE", "retDate": "_RETURN_DATE"}
    noReturn = checkRentHistory(rentHistory, keyMap)
#    print(noReturn)
    print(rentHistory[-1])
    lastIdx = rentHistory[-1]["SEQ"]

    for key in clib.rents:
        rent = clib.rents[key]
#        print(rent)
        if key in noReturn and rent["STATS"] == 0:
           user = noReturn[key]
           entry = {"SEQ": lastIdx + 1, "BOOK_CODE": key, "BOOK_STATE": 0, "USER_CODE": user, "REG_DATE": "2023-09-24 12:00:00"}
           rentHistory.append(entry)
           lastIdx += 1
        if rent["STATS"] in {1, 3} and key not in noReturn:
           entry = {"SEQ": lastIdx + 1, "BOOK_CODE": key, "BOOK_STATE": 1, "USER_CODE": rent["USERS"], "REG_DATE": rent["LENT_DATE"]}
           rentHistory.append(entry)
           lastIdx += 1

    print(f"DB size before rearrange {len(rentHistory)}")
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

    print(f"DB size after  rearrange {len(newList)}")

    historyLabels = clib.labels["RENTAL_HISTORY"]
#    print(historyLabels)

    for entry in newList:
        if entry["BOOK_CODE"] == "HK10002064":
            print(entry)

    if compareHistory(rentHistory, newList):
        print("No change")
        exit(0)

    print("Delete all entries")
    clib.db.UpdateQuery("delete from rental_history")

    print("Insert rearranged entried")
    for entry in newList:
        sqlEntry = dict()
        for label in historyLabels:
            if label == "RETURN_DATE":
                continue
            if label in entry:
                sqlEntry[label] = entry[label]
            else:
                print(f"{label} is missing in {entry}")
        label = dictToString(sqlEntry, labelOnly = True)
        value = dictToString(sqlEntry, valueOnly = True)
        queryStr = f"insert into rental_history ({label}) values ({value})"
        if sqlEntry["BOOK_CODE"] == "HK10002064":
            print(queryStr)
#        print(queryStr)
        clib.db.UpdateQuery(queryStr)


