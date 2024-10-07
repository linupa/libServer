import os
from pymongo import MongoClient
from dbUtil import *
import subprocess
import json
import hashlib
from datetime import datetime

def checkBook(mongoDb):
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

    return books


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

    db = checkBook(mongoDb)

    bookPath = 'hkmccBook'
    if not os.path.exists(bookPath):
        os.makedirs(bookPath)

    os.chdir(bookPath)

    bookJson = json.dumps(db, indent=1)
    sign = hashlib.md5(bookJson.encode('utf-8')).hexdigest()
    fileName = f"book_{sign}.json"
    fileNameJson = {"book": fileName}
    with open(f"book.info", "w") as outFile:
        json.dump(fileNameJson, outFile)

    files = os.listdir()
    prevBook = None
    for file in files:
        if file.find("book_") != 0 or ".json" not in file:
            continue
        prevBook = file
        break

    if prevBook:
        if prevBook == fileName:
            exit(0)
        command = f'git mv {prevBook} {fileName}'.split(' ')
        commit = subprocess.Popen(command, stdout=subprocess.PIPE)
        out, _ = commit.communicate()
        print(out)


    with open(fileName, "w") as outFile:
        outFile.write(bookJson)

    command = f'git add -u'.split(' ')
    commit = subprocess.Popen(command, stdout=subprocess.PIPE)
    out, _ = commit.communicate()
    print(out)

    today = datetime.now().strftime("%Y-%m-%d")

    command = f'git commit -m'.split(' ') + [f"Book update on {today}"]
    print(command)
    commit = subprocess.Popen(command, stdout=subprocess.PIPE)
    out, _ = commit.communicate()
    print(out)

    command = f'git push origin'.split(' ')
    print(command)
    commit = subprocess.Popen(command, stdout=subprocess.PIPE)
    out, _ = commit.communicate()
    print(out)

    serverInfo = mongoDb.serverInfo

    query = {"_id": "1"}
    values = {"$set":dict()}
    values["$set"]["book"] = sign
    print("Server Info " + str(values["$set"]))
    serverInfo.update_one(query, values)
