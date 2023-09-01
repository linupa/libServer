#!/usr/python3

from pymongo import MongoClient
from config import Config

password = Config['password']
connection = Config['connection'].format(password)

class MongoDB:
    def __init__(self, globalIp, localIp):

        print(f"Connection Info [{connection}]")
        self.client = MongoClient(connection)

        print("Done")

        db = self.client.library

        serverInfo = db.serverInfo

        query = {"_id": "1"}
        values = {"$set":dict()}
        values["$set"]["globalIp"] = globalIp
        values["$set"]["localIp"] = localIp
        values["$set"]["port"] = 8080
        print("Server Info " + str(values["$set"]))
        serverInfo.update_one(query, values)

        bookDb = db.book

        print('=' * 20)
        print('Read Books from MongoDB')
        self.mdBooks = dict()
        for book in bookDb.find():
            key = book['_id']
            self.mdBooks[key] = book

        print(f"Total {len(self.mdBooks)} books")

