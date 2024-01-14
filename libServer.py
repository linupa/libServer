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
from keyInput import KeyInput
from dbUtil import *
import requests
import socket
import dns.resolver
#import webbrowser
#from ocrTest import OCRTest

dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

global clib
global mdb
global keyInput
global globalIp
global localIp
global proxy

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/": {"origins": "*"}})
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

proxy = False

#@app.after_request
#def handle_options(response):
#    response.headers["Access-Control-Allow-Origin"] = "*"
#    response.headers['Access-Control-Allow-Credentials'] = "false"
#    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
#    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Requested-With"
#    response.credentials = False
#
#    return response

#################### GET #####################
@app.route('/', methods=['GET'])
def root():
    print("=" * 80)
    print("/")
    html = str()
    html += '<html>'
    html += '<header>'
    html += '<meta http-equiv="refresh" content="1; URL=https://goolibleee.github.io/hkmcclib" />'
    html += '</header>'
    html += '<body>'
    html += 'Redirect to HKMCC lib page'
    html += '</body>'
    html += '</html>'

    return html

@app.route('/check', methods=['GET'])
def check():
    print("=" * 80)
    print("Check")
    ipaddr = request.remote_addr
    print(ipaddr)
    adminPage = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    print(ipaddr)
    print(localIp)
    ret = dict()
    ret['check'] = 'Connection'
#    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp or ipaddr[0:7] != localIp[0:7])
    ret['admin'] = ("os" in request.args and "win" in request.args["os"].lower())
    ret['dueDate'] = clib.getDueDate()

    return jsonify(ret)

@app.route('/book', methods=['GET', 'OPTIONS'])
def findBook():
    print("=" * 80)
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
#    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    ret['admin'] = ("os" in request.args and "win" in request.args["os"].lower())
    print(ret)
    response = jsonify({'return': ret})
    return response

@app.route('/history', methods=['GET', 'OPTIONS'])
def getHistory():
    print("=" * 80)
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
#    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    ret['admin'] = ("os" in request.args and "win" in request.args["os"].lower())
    print(ret)
    response = jsonify({'return': ret})
    return response

@app.route('/user', methods=['GET', 'OPTIONS'])
def findUser():
    print("=" * 80)
    print("Find user")
    ipaddr = request.remote_addr
    print(request)
    print(len(request.args))
    userId = request.args.get("user", default = "None", type = str);
    print(f"Arguments [{userId}]")
    user = clib.findUser(userId)
    print(user)
    ret = dict()
#    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    ret['admin'] = ("os" in request.args and "win" in request.args["os"].lower())
    if user:
        ret = user
    response = jsonify({'return': ret})
    return response

@app.route('/users', methods=['GET', 'OPTIONS'])
def findUsers():
    print("=" * 80)
    print("Find users")
    ipaddr = request.remote_addr
    print(request)
    print(len(request.args))
    userId = request.args.get("user", default = "None", type = str);
    print(f"Arguments [{userId}]")
    users = clib.findUsers(userId)
#    print(users)
    ret = dict()
#    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    ret['admin'] = ("os" in request.args and "win" in request.args["os"].lower())
    if users:
        ret['data'] = users
    response = jsonify({'return': ret})
    return response

@app.route('/scanBarcode', methods=['OPTIONS', 'GET'])
@cross_origin()
def scanBarcode():
    ipaddr = request.remote_addr
    ret = dict()
    ret['scan'] = keyInput.read()
#    ret['admin'] = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    ret['admin'] = ("os" in request.args and "win" in request.args["os"].lower())
    response = jsonify(ret)
    return response


#################### POST #####################

@app.route('/user', methods=['POST'])
def updateUser():
    print("=" * 80)
    print("Update user")
    print(request)
    print(request.args)
    print(request.data)
    jsonStr = str(request.data, 'UTF-8')
    data = json.loads(jsonStr)
    if "os" in data:
        del data["os"]
    for key in data:
        base64value = data[key]
        print(f"Key: {key} Data: {data[key]}")
        data[key] = base64.b64decode(base64value).decode('utf-8')

    print(f"Arguments [{data}]")
    ret = clib.updateUserInfo(data)
    response = jsonify({"return": "OK" if ret else "FAIL"})
    return response

@app.route('/book', methods=['POST'])
def setBook():
    print("=" * 80)
    print("POST book")
    ipaddr = request.remote_addr
    jsonStr = str(request.data, 'UTF-8')
    ret = "FAILURE"
#    admin = (ipaddr == "127.0.0.1" or ipaddr == localIp)
#    admin = ("os" in request.args and "win" in request.args["os"].lower())
    if len(jsonStr) > 0 and (ipaddr == "127.0.0.1" or ipaddr == localIp):
        data = json.loads(jsonStr)
        admin = ("os" in data and "win" in data["os"].lower())
        print(data)
        ret = clib.setBookInfo(bookKey=data['book'], state=data['state'])
    response = jsonify({'return': ret})
    return response

@app.route('/checkOut', methods=['POST', 'OPTIONS'])
def checkOutBook():
    print("=" * 80)
    print("Check out")
    ipaddr = request.remote_addr
    jsonStr = str(request.data, 'UTF-8')
    print(jsonStr)
    ret = "FAILURE"
#    admin = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    if len(jsonStr) > 0:
        data = json.loads(jsonStr)
        admin = ("os" in data and "win" in data["os"].lower())
        ret = clib.checkOutBook(bookKey=data['book'], userKey=data['user'], admin=admin)
    response = jsonify({'return': ret})
    return response

@app.route('/extend', methods=['POST', 'OPTIONS'])
def extendBook():
    print("=" * 80)
    print("Extend")
    ipaddr = request.remote_addr
    jsonStr = str(request.data, 'UTF-8')
    print(jsonStr)
    ret = "FAILURE"
#    admin = (ipaddr == "127.0.0.1" or ipaddr == localIp)
    if len(jsonStr) > 0:
        data = json.loads(jsonStr)
        admin = ("os" in data and "win" in data["os"].lower())
        ret = clib.extendBook(bookKey=data['book'], admin=admin)
    response = jsonify({'return': ret})
    return response

@app.route('/return', methods=['POST', 'OPTIONS'])
def returnBook():
    print("=" * 80)
    print("Return")
    print(f"[{str(request.data, 'UTF-8')}]")
    jsonStr = str(request.data, 'UTF-8')
    print(jsonStr)
    ret = "FAILURE"
    if len(jsonStr) > 0:
        data = json.loads(jsonStr)
        ret = clib.returnBook(bookKey=data['book'])
    response = jsonify({'return': ret})
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

    #print('=' * 20)
    #print('Read Books from SQL')
    #key = list(clib.books.keys())[1]
    #print(clib.books[key])
    #print(clib.books[key].keys())

    print("Query cloud database")
    mdb = MongoDB(globalIp, localIp, proxy)
    #print(mdb.mdBooks[key])
    #print(mdb.mdBooks[key].keys())

    #print("Compare books")
    #compare(clib.books, mdb.mdBooks, sqlBookDict)

    keyInput = KeyInput()

    signal.signal(signal.SIGINT,handler)

#    webbrowser.open("https://tinyurl.com/hkmcclibtest")
#    from waitress import serve
#    serve(app, host="0.0.0.0", port=8080)
#    serve(app, host="0.0.0.0", port=8080, url_scheme='https')
    if proxy:
        app.run(host='0.0.0.0', port=8080)
    else:
        app.run(host='0.0.0.0', ssl_context=('cert.pem', 'key.pem'), port=8080)
