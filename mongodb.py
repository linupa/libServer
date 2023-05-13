#!/usr/python3

from pymongo import MongoClient
import requests
import socket
from config import Config

#password = 'qqZVFJoGERvCcoNI'
#connection = 'mongodb+srv://linupa:{}@hkmcclibrary.s59ur1w.mongodb.net/?retryWrites=true&w=majority'.format(password)
password = Config['password']
connection = Config['connection'].format(password)

class MongoDB:
    def __init__(self):
        api_url = "https://api.ipify.org/?format=json"
        response = requests.get(api_url)
        globalIp = response.json()['ip']
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        localIp = s.getsockname()[0]

        self.client = MongoClient(connection)

        db = self.client.library

        serverInfo = db.serverInfo

        query = {"_id": "1"}
        values = {"$set":dict()}
        values["$set"]["globalIp"] = globalIp
        values["$set"]["localIp"] = localIp
        values["$set"]["port"] = 8080
        print("Server Info " + str(values["$set"]))
        serverInfo.update_one(query, values)

