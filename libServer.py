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

global clib
global mdb

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/uploadImage": {"origins": "*"}})
CORS(app, supports_credentials=True, resources={r"/check": {"origins": "*"}})

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
    return jsonify({'some': 'data'})


@app.route('/checkOut', methods=['POST', 'OPTIONS'])
def checkOutBook():
    print("Check out")
    response = jsonify({'some': 'data'})
    data = json.loads(str(request.data, 'UTF-8'))
    ret = clib.checkOutBook(bookKey=data['book'], userKey=data['user'])
    response = jsonify({'return': ret})
    return response

@app.route('/return', methods=['POST', 'OPTIONS'])
def returnBook():
    print("Return")
    print(str(request.data, 'UTF-8'))
    print(request.data)
    data = json.loads(str(request.data, 'UTF-8'))
    print(data)
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
        print(data['image'][0:22])
        image = base64.b64decode((data['image'][22:]))
        print(len(image))
        print(type(image))
        print('Load image ' + str(type(image)))

        imgFile = open('image.png', 'wb')
        imgFile.write(image)
        imgFile.close()
        ocrTest = OCRTest()
        ret = ocrTest.readText('image.png')
        print(ret)
        response = jsonify({'return': ret})
    return response

def handler(signum, frame):
    print("Exit libServer")
    clib.close()
    exit(0)

if __name__ == '__main__':

    clib = CLibrary()

    mdb = MongoDB()
#    t2 = Thread(target=runGUI)
#    t2.start()

    signal.signal(signal.SIGINT,handler)

    from waitress import serve
#    serve(app, host="0.0.0.0", port=8080)
#    serve(app, host="0.0.0.0", port=8080, url_scheme='https')
    app.run(host='0.0.0.0', ssl_context=('cert.pem', 'key.pem'), port=8080)

