from pymongo import MongoClient
from config import Config
from clibrary import CLibrary, dictToString
from dbUtil import *

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

def compareEntry(hist):
    return hist['timestamp']

def compareHistory(orig, modi):
    if len(orig) != len(modi):
        return False
    length = len(orig)
    for i in range(length):
        origItem = orig[i]
        modiItem = modi[i]
        if (origItem['_id'] != modiItem['_id'] or
            origItem['book_id'] != modiItem['book_id'] or
            origItem['book_state'] != modiItem['book_state'] or
            origItem['user_id'] != modiItem['user_id'] or
            origItem['timestamp'] != modiItem['timestamp']):
            return False
    return True

if __name__ == '__main__':
    client = MongoClient(connection)
    db = client.library_test

    rentHistory = mdb2list(db.rentLog)
    print(rentHistory[0])

    print(len(rentHistory))
    rentHistory.sort(key=compareEntry)
    print(rentHistory[0])
    newList = list()
    currentIds = list()
    for entry in rentHistory:
        length = len(newList)
        currentIds.append(entry['_id'])
        entry = entry.copy()
        if entry['_id'] > 1000000:
            print(entry)
        count = 1
        dup = False
        while count < length and newList[-count]['timestamp'] == entry['timestamp']:
            lastItem = newList[-count]
            if (lastItem['book_id'] == entry['book_id'] and
                lastItem['book_state'] == entry['book_state'] and
                lastItem['user_id'] == entry['user_id']):
                print(f"Duplicate item {entry}")
                dup = True
                break
            count += 1
        if not dup:
            entry['_id'] = len(newList) + 1
            newList.append(entry)

    print(len(newList))
    print(newList[0])

    if compareHistory(rentHistory, newList):
        print("No change")
#        exit(0)

    print("Changed")
    updates = [list(), list(), currentIds]
    updateCloud(updates, None, db.rentLog)
    print("Deleted all records")

    newDict = dict()
    newIds = list()
    for entry in newList:
        idx = entry['_id']
        newDict[idx] = entry
        newIds.append(idx)

    updates = [newIds, list(), list()]
    updateCloud(updates, newDict, db.rentLog)


    '''
    print("Delete all entries")
    clib.db.UpdateQuery("delete from rental_history")

    for entry in newList:
        if "RETURN_DATE" in entry:
            del entry["RETURN_DATE"]
        label = dictToString(entry, labelOnly = True)
        value = dictToString(entry, valueOnly = True)
        queryStr = f"insert into rental_history ({label}) values ({value})"
        print(queryStr)
        clib.db.UpdateQuery(queryStr)
    '''
