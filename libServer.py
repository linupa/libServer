#!/bin/python3

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import base64
import json
from threading import *
import time
from clibrary import CLibrary
import signal
from mongodb import MongoDB
from ocrTest import OCRTest
from keyInput import KeyInput
from dbUtil import *
import requests
import socket
import dns.resolver
#import webbrowser

dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

global clib
global mdb
global keyInput
global globalIp
global localIp

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/uploadImage": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/check": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/checkOut": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/extend": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/return": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/user": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/users": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/book": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/history": {"origins": "*"}})

image = None

#@app.after_request
#def handle_options(response):
#    response.headers["Access-Control-Allow-Origin"] = "*"
#    response.headers['Access-Control-Allow-Credentials'] = "false"
#    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
#    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Requested-With"
#    response.credentials = False
#
#    return response

@app.route('/check', methods=['GET'])
def check():
    print("Check")
    ipaddr = request.remote_addr
    print(ipaddr)
    adminPage = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    print(ipaddr)
    print(localIp)
    ret = dict()
    ret['check'] = 'Connection'
    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    ret['dueDate'] = clib.getDueDate()

    return jsonify(ret)

@app.route('/book', methods=['GET', 'OPTIONS'])
def findBook():
    print("Find book")
    ipaddr = request.remote_addr
    print(request)
    print(request.args)
    print(len(request.args))

    jsonStr = str(request.data, 'UTF-8')
    print(jsonStr)

    bookId = request.args.get("book", default = "None", type = str)
    match = request.args.get("match", default = "false", type = str)
    userId = request.args.get("user", default = "None", type = str)
#    bookId = base64.b64decode(bookId).decode('utf-8')
    print(f"Arguments [{bookId}] [{match}]")
    ret = dict()
    if bookId != "None":
        book = clib.findBook(bookId = bookId, match = match)
        ret['books'] = book
    elif userId != "None":
        book = clib.findBook(userId=userId)
        ret['books'] = book
    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    print(ret)
    response = jsonify({'return': ret})
    return response

@app.route('/history', methods=['GET', 'OPTIONS'])
def getHistory():
    print("Get history")
    ipaddr = request.remote_addr
    print(request)
    print(request.args)
    print(len(request.args))
    period = request.args.get("period", default = "None", type = str)
#    bookId = base64.b64decode(bookId).decode('utf-8')
    print(f"Arguments [{period}]")
    ret = dict()
    book = clib.getHistory(period = period)
    ret['books'] = book
    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    print(ret)
    response = jsonify({'return': ret})
    return response

@app.route('/user', methods=['GET', 'OPTIONS'])
def findUser():
    print("Find user")
    ipaddr = request.remote_addr
    print(request)
    print(len(request.args))
    userId = request.args.get("user", default = "None", type = str);
    print(f"Arguments [{userId}]")
    user = clib.findUser(userId)
    print(user)
    ret = dict()
    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    if user:
        ret = user
    response = jsonify({'return': ret})
    return response

@app.route('/user', methods=['POST'])
def updateUser():
    print("Update user")
    print(request)
    print(request.args)
    print(request.data)
    jsonStr = str(request.data, 'UTF-8')
    data = json.loads(jsonStr)
    for key in data:
        base64value = data[key]
        data[key] = base64.b64decode(base64value).decode('utf-8')

    print(f"Arguments [{data}]")
    ret = clib.updateUserInfo(data)
    response = jsonify({"return": "OK" if ret else "FAIL"})
    return response

@app.route('/users', methods=['GET', 'OPTIONS'])
def findUsers():
    print("Find users")
    ipaddr = request.remote_addr
    print(request)
    print(len(request.args))
    userId = request.args.get("user", default = "None", type = str);
    print(f"Arguments [{userId}]")
    users = clib.findUsers(userId)
#    print(users)
    ret = dict()
    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    if users:
        ret['data'] = users
    response = jsonify({'return': ret})
    return response

@app.route('/book', methods=['POST'])
def setBook():
    print("POST book")
    ipaddr = request.remote_addr
    jsonStr = str(request.data, 'UTF-8')
    ret = "FAILURE"
    admin = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    if len(jsonStr) > 0 and (ipaddr == "127.0.0.1" or ipaddr == localIp):
        data = json.loads(jsonStr)
        print(data)
        ret = clib.setBookInfo(bookKey=data['book'], state=data['state'])
    response = jsonify({'return': ret})
    return response

@app.route('/checkOut', methods=['POST', 'OPTIONS'])
def checkOutBook():
    print("Check out")
    ipaddr = request.remote_addr
    jsonStr = str(request.data, 'UTF-8')
    print(jsonStr)
    ret = "FAILURE"
    admin = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    if len(jsonStr) > 0:
        data = json.loads(jsonStr)
        ret = clib.checkOutBook(bookKey=data['book'], userKey=data['user'], admin=admin)
    response = jsonify({'return': ret})
    return response

@app.route('/extend', methods=['POST', 'OPTIONS'])
def extendBook():
    print("Extend")
    ipaddr = request.remote_addr
    jsonStr = str(request.data, 'UTF-8')
    print(jsonStr)
    ret = "FAILURE"
    admin = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    if len(jsonStr) > 0:
        data = json.loads(jsonStr)
        ret = clib.extendBook(bookKey=data['book'], admin=admin)
    response = jsonify({'return': ret})
    return response

@app.route('/return', methods=['POST', 'OPTIONS'])
def returnBook():
    print("Return")
    print(str(request.data, 'UTF-8'))
    jsonStr = str(request.data, 'UTF-8')
    print(jsonStr)
    ret = "FAILURE"
    if len(jsonStr) > 0:
        data = json.loads(jsonStr)
        ret = clib.returnBook(bookKey=data['book'])
    response = jsonify({'return': ret})
    return response

@app.route('/uploadImage', methods=['POST', 'OPTIONS', 'GET'])
@cross_origin()
def uploadImage():
    global image
    print("image uploaded")
#    response = jsonify({'return': "OK"})
#    response.headers.add('Access-Control-Allow-Origin', '*')
#    print(len(request.data))
    if len(request.data) > 0:
        data = json.loads(str(request.data, 'UTF-8'))
        image = base64.b64decode((data['image'][22:]))
        print(len(image))
        print(type(image))
        print('Load image ' + str(type(image)))

        imgFile = open('image.jpg', 'wb')
        imgFile.write(image)
        imgFile.close()
        ocrTest = OCRTest()
        candidates = ocrTest.readText('image.jpg')
        print(candidates)
        ret = dict()
        for candidate in candidates:
            book = clib.findBook(candidate)
            if book:
                ret = book
                break;

        print(ret);
        response = jsonify({'return': ret})
    return response

@app.route('/scanBarcode', methods=['OPTIONS', 'GET'])
@cross_origin()
def scanBarcode():
    ipaddr = request.remote_addr
    ret = dict()
    ret['scan'] = keyInput.read()
    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    response = jsonify(ret)
    return response

def handler(signum, frame):
    print("Exit libServer")
    clib.close()
    exit(0)

if __name__ == '__main__':

    print("Query IP address")
#    api_url = "https://ipv4.seeip.org/jsonip"
    api_url = "https://api.ipify.org/?format=json"
    response = requests.get(api_url)
    globalIp = response.json()['ip']
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))
    localIp = s.getsockname()[0]

    print("Query local database")
    clib = CLibrary()

    print('=' * 20)
    print('Read Books from SQL')
    key = list(clib.books.keys())[1]
    print(clib.books[key])
    print(clib.books[key].keys())

    print("Query cloud database")
    mdb = MongoDB(globalIp, localIp)
    print(mdb.mdBooks[key])
    print(mdb.mdBooks[key].keys())

    count = 0

    print("Compare books")
    compare(clib.books, mdb.mdBooks, sqlBookDict)

#    for entry in clib.rentHistory:
#        if entry['BOOK_CODE'] == 'HK00004322':
#            print(entry)

    keyInput = KeyInput()
#    t2 = Thread(target=runGUI)
#    t2.start()

    signal.signal(signal.SIGINT,handler)

#    webbrowser.open("https://tinyurl.com/hkmcclibtest")
    from waitress import serve
#    serve(app, host="0.0.0.0", port=8080)
#    serve(app, host="0.0.0.0", port=8080, url_scheme='https')
    app.run(host='0.0.0.0', ssl_context=('cert.pem', 'key.pem'), port=8080)
