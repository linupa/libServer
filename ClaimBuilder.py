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
'<title> Claim </title>',
'<style>',
'table {',
'    border-collapse: collapse;',
'}',
'tr {'
'}',
'td.claim {',
'    font-family: gulim;',
'    border: 2px solid lightgray;',
'    width: 100px;',
'    height: 100;',
'    text-align: center;',
'    margin: 0px;',
'    font-size: 90%;',
'}',
'td.barcode {',
'    font-family: gulim;',
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

class ClaimBuilder:
    def __init__(self, books):
        self.books = books

    def getList(self, filters):
        showBooks = list()
        for key in self.books:
            book = self.books[key]
            if "REG_DATE" not in book:
                continue
            if "DELETE_YN" in book and book["DELETE_YN"] == "Y":
                continue

            barcode = book["BARCODE"]
            regDate = book["REG_DATE"][0:10]
            if "fromDate" not in filters:
                continue

            fromDate = filters["fromDate"]
            fromLength = len(fromDate)
            if regDate[:fromLength] < fromDate:
                continue
            elif "toDate" in filters:
                toDate = filters["toDate"]
                toLength = len(toDate)
                if regDate[:toLength] > toDate:
                    continue
            elif regDate[:fromLength] > fromDate:
                continue

            if "barcode" in filters and barcode[0:len(filters["barcode"])] != filters["barcode"]:
                continue

            if "category" in filters:
                catFilter = filters["category"]
                cat = book["CATEGORY"]
                if catFilter in {"2", "8"}:
                    if catFilter != cat[0]:
                        continue
                elif cat[0] in {"2", "8"}:
                    continue

            showBooks.append(book)

        showBooks.sort(key=bookKey)

        return showBooks

    def generateHtml(self, showBooks, fileName):
        rows = list()
        rows.append(list())
        lastRow = rows[-1]
        for book in showBooks:
            if len(lastRow) == 8:
                rows.append(list())
                lastRow = rows[-1]
            lastRow.append(book)
        with codecs.open(fileName, "w", "utf-8") as f:
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


if __name__ == '__main__':
    # Read SQL
    clib = CLibrary()
    print("Got clib")
    if len(sys.argv) < 2:
        exit(-1)

    filters = dict()
    checkDate = sys.argv[1]
    filters["fromDate"] = checkDate
    toDate = None
    if len(sys.argv) >= 3:
        toDate = sys.argv[2]
        filters["toDate"] = toDate

    print(checkDate)
    print(toDate)

    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    db = client.library
    print("Check")

    print("="*80)
    print("Book")
    books = convertToSQL(db.book, "BARCODE", sqlBookDict)

    claimBuilder = ClaimBuilder(books)

    showBooks = claimBuilder.getList(filters)

    print(f"{len(showBooks)} book(s) added on {checkDate}")

    claimBuilder.generateHtml(showBooks, "claim.html")
    filename = 'file:///' + os.getcwd() + "/" + 'claim.html'
    webbrowser.open_new_tab(filename)
