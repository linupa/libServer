import datetime
import base64
import rsa
import requests
import subprocess

sqlBookDict = {
    'SEQ': 'seqnum',
    'BARCODE': '_id',
    'RFID': 'rfid',
    'BOOKNAME': 'title',
    'BOOKNUM': 'num',
    'AUTHOR': 'author',
    'TOTAL_NAME': 'series',
    'CATEGORY':'category',
    'AUTHOR_CODE':'author_code',
    'CLAIMNUM': 'claim_num',
    'COPYNUM': 'copy_num',
    'EX_CATE': 'ex_cate',
    'ISBN': 'isbn',
    'PUBLISH': 'publisher',
    'ATTACH': 'attach',
    'CLAIM': 'claim',
    'LOCATION': 'location',
    'BOOKIN': 'book_in',
    'REG_DATE': 'registration_date',
    'MOD_DATE': 'modification_date',
    'DELETE_YN': 'deleted'
}

sqlMARCDict = {
    'SEQ': '_id',
    'MARC_DATA': 'MARC_DATA',
    'DELETE_YN': 'DELETE_YN'
}

sqlUserDict = {
    'SEQ': "seqnum",
    'USER_CODE': "_id",
    'USER_NAME': "name",
    'PHONE_NUMBER': "phone",
    'ADDRESS': "address",
    'EMAIL': "email",
    'USER_LEVEL': "level",
    'USER_STATE': "state",
    'NOTICE': "memo",
    'USER_IMAGE': "image_path",
    'DISABLE_DATE': "disabled_until",
    'DELAY_DAY': "delayed_days",
    'DELAY_CHARGE': "delay_charge",
    'REG_DATE': "registration_date",
    'MOD_DATE': "modification_date",
    'DELETE_YN': "deleted"
}

sqlRentDict = {
    'SEQ': "_id",
    'BARCODE': "book_id",
    'STATS': "state",
    'USERS': "user_id",
    'LENT_DATE': "rent_date",
    'RETURN_DATE': "return_date",
    'RESERVE_USER': "reserve_user_id",
    'RESERVE_DATE': "reserve_date",
    'EXTEND_COUNT': "extend_count",
    'DELETE_YN': "deleted",
    'ATTACH': "attach",
    'ATTACH_USER': "attach_user"
}

sqlRentHistoryDict = {
    'SEQ': "_id",
    'BOOK_CODE': "book_id",
    'BOOK_STATE': "book_state",
    'USER_CODE': "user_id",
    'REG_DATE': "timestamp",
    '_RETURN_DATE': "return_date"
}
def logKey(entry, key='timestamp'):
    return datetime.datetime.strptime(entry[key], "%Y-%m-%d %H:%M:%S")

def toNumber(numStr):
    ret = ""
    if not numStr:
        return ret
    for i in range(len(numStr)):
        if numStr[i].isnumeric():
            ret = ret + numStr[i]
    return ret

def timeToString(t, dateOnly = False):
    if dateOnly:
        return t.strftime("%Y-%m-%d")
    else:
        return t.strftime("%Y-%m-%d %H:%M:%S")

def stringToTime(s, dateOnly = False):
    if s.find(":") > 0 and not dateOnly:
        form = '%Y-%m-%d %H:%M:%S'
    else:
        form = '%Y-%m-%d'
    return datetime.datetime.strptime(s, form)

def mdb2dict(srcList: list, key = '_id', callback = None, interval = 1000):
    dstDict = dict()
    count = 0
    for src in srcList.find():
        keyValue = src[key]
        dstDict[keyValue] = src
        if callback and count % interval == 0:
            callback(count)
        count += 1
    if callback:
        callback(count)
    return dstDict

def mdb2list(srcList: list, key = '_id'):
    dstList = list()
    for src in srcList.find():
        dstList.append(src)
    return dstList

def list2dict(srcList: list, key = '_id'):
    dstDict = dict()
    for src in srcList:
        keyValue = src[key]
        dstDict[keyValue] = src
    return dstDict

def dict2list(srcDict: dict):
    dstList = list()
    for key in srcDict:
        dstList.append(srcDict[key])
    return dstList

def dictToString(d, labelOnly = False, valueOnly = False):
    l = list()
    for key in d:
#        if isinstance(d[key], int):
#            value = str(d[key])
#        else:
        if key[0] == '_':
            continue
        value = "'{}'".format(d[key])

        if labelOnly:
            l.append(f"{key}")
        elif valueOnly:
            l.append(value)
        else:
            l.append(f"{key}={value}")
    return ", ".join(l)

def dictToString2(d, valueOnly = False):
    l = list()
    for key in d:
#        if isinstance(d[key], int):
#            value = str(d[key])
#        else:
        if key[0] == '_':
            continue
        if valueOnly:
           l.append(d[key])
        else:
           l.append(f"{key}=?")
    if valueOnly:
        return l
    return ", ".join(l)

def updateSQL(updates, srcEntries, clib, dbName, keyName, callback = None, interval = 100):
    totalCount = len(updates[0]) + len(updates[1]) + len(updates[2])
    if totalCount == 0:
        totalCount = 1
    count = 0
    for entry in updates[2]:
        count += 1
        if callback and (count%interval) == 0:
            callback(100 * count / totalCount)
        try:
            clib.db.UpdateQuery(f"delete from {dbName} where {keyName}='{entry}'")
        except Exception as e:
            print(e)

    for key in updates[0]:
        entry = srcEntries[key]
        label = dictToString(entry, labelOnly = True)
        value = dictToString2(entry, valueOnly = True)
        queryStr = "insert into {} ({}) values ({})".format(dbName, label, ','.join(['?'] * len(value)))
        count += 1
        if callback and (count%interval) == 0:
            callback(100 * count / totalCount)
        try:
            clib.db.UpdateQueryWithValue(queryStr, value)
        except Exception as e:
            print(e)

    for key in updates[1]:
        entry = srcEntries[key]
        label = dictToString2(entry)
        value = dictToString2(entry, valueOnly = True)
#        queryStr = "update {} set \{{}\} where {}='{}'".format(dbName, label, keyName, key)
        queryStr = f"update {dbName} set {label} where {keyName}='{key}'"
#        print(queryStr)
#        print(value)
        count += 1
        if callback and (count%interval) == 0:
            callback(100 * count / totalCount)
        try:
            clib.db.UpdateQueryWithValue(queryStr, value)
        except Exception as e:
            print(e)
    if callback:
        callback(100)

def updateCloud(updates, srcEntries, dstEntries, callback = None):
    totalCount = len(updates[0]) + len(updates[1]) + len(updates[2])
    if totalCount == 0:
        totalCount = 1
    count = 0

#    return

    print("Add")
    adds = updates[0].copy()
    while len(adds) > 0:
        newEntries = list()
        while len(newEntries) < 100 and len(adds) > 0:
            key = adds.pop(0)
            newEntries.append(srcEntries[key])
        if len(newEntries) > 0:
            print(f"\rRemaining {len(adds)}", end="", flush=True)
            dstEntries.insert_many(newEntries)
        print("")

    count = 0
    print("Delete")
    for key in updates[2]:
        query = {'_id': key}
        dstEntries.delete_one(query)
        if (count%100) == 0:
            print(f"\rProgress {count}", end="", flush=True)
        count +=1
    print("")

    count = 0
    print("Update")
    for key in updates[1]:
        query = {'_id': key}
        newValue = {"$set":dict()}
        for label in srcEntries[key]:
            newValue["$set"][label] = srcEntries[key][label]
        dstEntries.update_one(query, newValue)
        if (count%100) == 0:
            print(f"\rProgress {count}", end="", flush=True)
#        print(newValue)
        count +=1
    print("")

    if callback:
        callback(100)

def encryptUserInfo(users):

    if "GITHUB_ACTIONS" in os.environ:
        prk = ""
    else:
        from config import Config
        prk = rsa.PrivateKey.load_pkcs1(Config['key'],'PEM')

    for key in users:
        user = users[key]
        if user['deleted'] == "Y":
            continue
        email = user['email']
        phone = user['phone']
        phone = toNumber(phone)
#        if len(phone) != 10:
#            print(user)
        user['encrypted_phone'] = ""
        user['encrypted_email'] = ""
        if phone and len(phone) > 0:
            try:
                encryptedPhone = base64.b64encode(rsa.sign(phone.encode('ascii'), prk, 'SHA-256'))
                user['encrypted_phone'] = encryptedPhone.decode('ascii')
            except Exception as e:
                print("Exception while encrypting phone")
        if email and len(email) > 0:
            try:
                encryptedEmail = base64.b64encode(rsa.sign(email.encode('ascii'), prk, 'SHA-256'))
                user['encrypted_email'] = encryptedEmail.decode('ascii')
            except Exception as e:
                print("Exception while encrypting email")

def convertEntryToMDB(fromDb: dict, key: str, conversion: dict):
    converted = list()
    dst = dict()
    for srcKey in src:
        if srcKey not in conversion:
            continue
        dstKey = conversion[srcKey]
        dst[dstKey] = src[srcKey]
    return dst

def convertToMDB(fromDb: dict, key: str, conversion: dict):
    converted = list()
    for seqId in fromDb:
        if type(fromDb) is dict:
            src = fromDb[seqId]
        else:
            src = seqId
        dst = dict()
        for srcKey in src:
            if srcKey not in conversion:
                continue
            dstKey = conversion[srcKey]
            dst[dstKey] = src[srcKey]
        converted.append(dst)
    converted = makeUnique(converted, key)

    return converted

def convertEntryToSQL(mdbEntry, revConv: dict):
    conversion = dict()
    for convKey in revConv:
        value = revConv[convKey]
        conversion[value] = convKey

    dstEntry = dict()
    for valueKey in mdbEntry:
        if valueKey not in conversion:
            continue
        dstEntry[conversion[valueKey]] = mdbEntry[valueKey]
    if 'ATTACH' in dstEntry and not dstEntry['ATTACH']:
        dstEntry["ATTACH"] = "N"
    if 'ATTACH_USER' in dstEntry and not dstEntry['ATTACH_USER'] == "":
        dstEntry['ATTACH'] = ""

    return dstEntry

def convertToSQL(mdb, key, revConv: dict, callback = None, interval = 100):
    conversion = dict()
    for convKey in revConv:
        value = revConv[convKey]
        conversion[value] = convKey

    mdbDict = mdb2dict(mdb, callback= callback, interval= interval)

    dstDict = dict()
    for mdbKey in mdbDict:
        mdbEntry = mdbDict[mdbKey]
        dstEntry = dict()
        for valueKey in mdbEntry:
            if valueKey not in conversion:
                continue
            dstEntry[conversion[valueKey]] = mdbEntry[valueKey]
        if 'ATTACH' in dstEntry and not dstEntry['ATTACH']:
            dstEntry["ATTACH"] = "N"
        if 'ATTACH_USER' in dstEntry and not dstEntry['ATTACH_USER'] == "":
            dstEntry['ATTACH'] = ""
        dstDict[dstEntry[key]] = dstEntry

    return dstDict

def checkUnique(src, key: str = '_id'):
    ids = dict()
    if type(src) == list:
        for entry in src:
            keyValue = entry[key]
            if keyValue in ids:
                print(f"Duplicated ID {keyValue} {ids[keyValue]}->{entry['REG_DATE']}")
            else:
                ids[entry[key]] = entry['REG_DATE']
#            if entry[key] >= 6693 and entry[key] <= 6701:
#                print(entry)
    elif type(src) == dict:
        for srcKey in src:
            entry = src[srcKey]
            keyValue = entry[key]
            if keyValue in ids:
                print(f"Duplicated ID {keyValue} {ids[keyValue]} {entry['REG_DATE']}")
            else:
                ids[entry[key]] = entry['REG_DATE']

def makeUnique(l: list, key: str = '_id'):
    d = dict()
    for entry in l:
        id = entry[key]
        isInteger = (type(id) == int)

        while id in d:
            if type(id) == int:
                id += 100000000000
            elif type(id) == str:
                try:
                    idInt = int(id)
                    id = idInt + 100000000000
                except Exception as e:
                    id += "x"
            else:
                print(f"Unknown type {type(id)}")
                break

        id = int(id) if isInteger else str(id)
        if entry[key] != id:
            print(f"Duplicated ID {entry[key]} -> {id}")
            entry[key] = id
        d[id] = entry

#    l = list()
#    for key in d:
#        l.append(d[key])

    return d

ignoreTag = {"encrypted_email", "encrypted_phone", "modification_date"}
ignoreTag.update({"attach", "ATTACH", "attach_user", "ATTACH_USER"})
def compare(srcEntries: dict, dstEntries: dict, conversion:dict = None, log = False):
    addedList = list()
    modifiedList = list()
    deletedList = list()

    if log:
        print("LOG enabled")
        print(f"{len(srcEntries)} {len(dstEntries)}")
    dstFlag = set()
    for key in dstEntries:
        dstFlag.add(key)
    print(len(dstFlag))

#    for gsEntry in srcEntries:
#        key = gsEntry['_id']
    for key in srcEntries:
        gsEntry = srcEntries[key]
        if key not in dstFlag:
            if log:
                print("=== New entry")
                print(gsEntry)
            addedList.append(key)
            continue
        mdEntry = dstEntries[key]

        dstFlag.remove(key)
        modified = False
        for label in gsEntry:
            if conversion:
                if label not in conversion:
                    continue
                mLabel = conversion[label]
            else:
                mLabel = label
            if label in ignoreTag or mLabel in ignoreTag:
                continue
            if mLabel not in mdEntry:
                if log:
                    print(f'Label {mLabel} is not in MongoDB')
                modified = True
            elif gsEntry[label] != mdEntry[mLabel]:
#                if log:
#                   print(f'{key} Value for label {label}/{mLabel} is different')
#                   print(f"{gsEntry[label]} != {mdEntry[mLabel]}")
                modified = True
            if "return_data" in mdEntry:
                modified = True
        if modified:
            modifiedList.append(key)
    if len(dstFlag) > 0:
        print("Deleted entries")
        for key in dstFlag:
#            if log:
#                print(dstEntries[key])
            deletedList.append(key)
    print(f'Update Add/Mod/Del {len(addedList)} {len(modifiedList)} {len(deletedList)}')
    if len(addedList) > 0:
        print(f"Add    {srcEntries[addedList[0]]}")
#    for entry in addedList:
#        print(srcEntries[entry])
#        if log:
#            print(addedList)
    if len(modifiedList) > 0:
        print(f"Update {srcEntries[modifiedList[0]]}")
        print(f"       {dstEntries[modifiedList[0]]}")
#        if log:
#            print(modifiedList)
    if len(deletedList) > 0:
        print(f"Delete {dstEntries[deletedList[0]]}")
#        if log:
#            print(deletedList)
    return [addedList, modifiedList, deletedList]

def logCompare(log):
    if "timestamp" in log:
        return log["timestamp"]
    elif "date" in log:
        return log["date"]
    else:
        return 0


def checkRentHistory(rentlog: list, keyMap: dict):
    idxKey = keyMap["idx"]
    bookKey = keyMap["book"]
    stateKey = keyMap["state"]
    userKey = keyMap["user"]
    dateKey = keyMap["date"]
    retKey = keyMap["retDate"]

    rentlog.sort(key=logCompare)

    print("Check rent history validity...")
    rentLogList = list()
    for i in range(len(rentlog)):
        logCopy = rentlog[i].copy()
        logCopy[idxKey] = i
        rentLogList.append(logCopy)

    numCheckout = 0
    numReturn = 0
    noReturn = dict()
    for i in range(len(rentLogList)):
        log = rentLogList[i]
        idx = log[idxKey]
        bookId = log[bookKey]
        state = log[stateKey]
        timestamp = log[dateKey]
        user = log[userKey]
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
                if bookId != log2[bookKey]:
                    continue
                if log2[stateKey] in {0, '0'} and user == log2[userKey]:
                    returned = True
                    break
                if not otherRent and log2[stateKey] in {1, '1'} and user != log2[userKey]:
                    otherRent = True
                    otherRentDate = log2[dateKey]
            if returned:
                rentlog[idx][retKey] = log2[dateKey]
            elif otherRent:
                rentlog[idx][retKey] = otherRentDate
            else:
                noReturn[bookId] = user
        if state in {0, '0'}:
            numReturn += 1
#        if log['SEQ'] == 352:
#            print(f"{idx} Returned {rentlog[idx]} {type(state)} {log['SEQ']} ~ {log2['SEQ']}")
    print(f"Checkout: {numCheckout}, Return: {numReturn}, NoReturn: {len(noReturn)}")
    return noReturn

def reportServerLog(db, action, misc = dict()):
    report = dict()
    report.update(misc)
    report["action"] = action
    api_url = "https://api.ipify.org/?format=json"
    response = requests.get(api_url)
    report["ip"] = response.json()['ip']
    report["time"] = str(datetime.datetime.now())
    commit = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE)
    out, _ = commit.communicate()
    report["commit"] = out.decode().strip()

    db.serverLog.insert_one(report)


