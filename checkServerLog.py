import os
from pymongo import MongoClient
from dbUtil import *
from marc import MARC
from authorCode import getAuthorCode
import subprocess
from text import getText
import datetime
import argparse

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
    print("serverLog")
    serverLog = mdb2dict(mongoDb.serverLog)
    print(f"{len(serverLog)} serverLog")

    return [books, users, serverLog]

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--date')
    parser.add_argument('-i', '--id')

    args = parser.parse_args()
    # Open MongoDB
    if "GITHUB_ACTIONS" in os.environ:
        password = os.environ["MONGODB_PASSWORD"]
    else:
        from config import Config
        password = Config['password']
    connection = Config['connection'].format(password)
    client = MongoClient(connection)
    mongoDb = client.library

    try:
        [books, users, serverLog] = checkDB(mongoDb)
    except Exception as e:
        print("checkDB failed")
        print(e)
        exit()
#    keys = list(serverLog.keys())
#    print(serverLog[keys[-1]])
    if args.date:
        for key in serverLog:
            log = serverLog[key]
            if args.date in log["time"]:
                del log["book"]
                del log["marc"]
                del log["user"]
                del log["rent"]
                del log["rentHistory"]
                print(log)
    elif args.id:
        rented = list()
        returned = list()
        for key in serverLog:
            if str(key) == args.id:
                log = serverLog[key]
                rent = log["rentHistory"]
                del log["book"]
                del log["marc"]
                del log["user"]
                del log["rentHistory"]
                for key in log:
                    print(f"{key}: {log[key]}")
                if "del" in rent:
                    for entry in rent["del"]:
                        bookCode = entry["BOOK_CODE"]
                        userCode = entry["USER_CODE"]
                        if bookCode in books:
                            entry["BOOK"] = books[bookCode]['title']
                        if userCode in users:
                            entry["USER"] = users[userCode]['name']
                        if entry['BOOK_STATE'] == 1:
                            rented.append(entry)
                        elif entry['BOOK_STATE'] == 0:
                            returned.append(entry)
        print("=== Rented   ===")
        for entry in rented:
            print(entry)
        print("=== Returned ===")
        for entry in returned:
            print(entry)
