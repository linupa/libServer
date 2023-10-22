import sys
import codecs
from pymongo import MongoClient
from config import Config
from clibrary import CLibrary
from dbUtil import *
import os
import webbrowser

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

htmlStr1 = [
'<html lang="en">'
'<head>'
'<title> Clain </title>',
'<style>',
'table {',
'    border-collapse: collapse;',
'}',
'tr {'
'}',
'td.claim {',
'    border: 2px solid lightgray;',
'    width: 100px;',
'    height: 100;',
'    text-align: center;',
'    margin: 0px;',
'    font-size: 90%;',
'}',
'td.barcode {',
'    border: 2px solid lightgray;',
'    width: 100px;',
'    height: 30px;',
'    text-align: center;',
'    margin: 0px;',
'    font-size: 90%;',
'}',
'@media print',
'{',
'.pagebreak {page-break-before:always}',
'}',
'</style>',
'</head>'
'<body>'
]
htmlStr2 = [
'</tbody></table>'
'</body>'
]

def bookKey(book):
    return book["BARCODE"]

if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()
    print("Got clib")
    if len(sys.argv) < 2:
        exit(-1)

    checkDate = sys.argv[1]
    print(checkDate)

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library
    print("Check")

    print("="*80)
    print("Book")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict)

    count = 0
    showBooks = list()
    for key in books:
        book = books[key]
        if "REG_DATE" not in book:
            continue

        regDate = book["REG_DATE"][0:10]
        if regDate == checkDate:
            showBooks.append(book)
        count += 1
    showBooks.sort(key=bookKey)
    rows = list()
    rows.append(list())
    lastRow = rows[-1]
    for book in showBooks:
        if len(lastRow) == 8:
            rows.append(list())
            lastRow = rows[-1]
        lastRow.append(book)

    with codecs.open("claim.html", "w", "utf-8") as f:
        for entry in htmlStr1:
            f.write(entry + "\n")
        f.write('<table><tbody>\n')
        for idx, row in enumerate(rows):
            if idx != 0 and (idx % 6) == 0:
                f.write('</tbody></table>\n')
                f.write('<table class="pagebreak"><tbody>\n')
            f.write("<tr>\n")
            for entry in row:
                barcode = entry['BARCODE']
                claim = entry['CLAIM']
                info = str(entry['CLAIM']).split("_")
                if barcode[0:3] == "HK0":
                    info[0] = "아동"
                count = 0
                while count < len(info):
                    if len(info[count]) == 0:
                        del info[count]
                    count += 1
                info = "<br>".join(info)
                f.write(f'<td class="claim"> {info} </td>\n')
            f.write('</tr><tr class="barcode">\n')
            for entry in row:
                barcode = entry['BARCODE']
                f.write(f'<td class="barcode"> {barcode} </td>\n')
            f.write("</tr>\n")
        f.write('</tbody></table>\n')

        for entry in htmlStr2:
            f.write(entry + "\n")

        filename = 'file:///' + os.getcwd() + "/" + 'claim.html'
        webbrowser.open_new_tab(filename)
