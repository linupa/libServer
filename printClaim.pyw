import os
import webbrowser
import tkinter as tk
import tkinter.messagebox
import tksheet
import threading

from config import Config
from pymongo import MongoClient
from ClaimBuilder import ClaimBuilder
from dbUtil import *
from Text import text

def callback(count):
    print(count)

if __name__ == '__main__':
  path = __file__

  if "/" in path:
    delimiter = "/"
  else:
    delimiter = "\\"
  paths = path.split(delimiter)[0:-1]
  path = "/".join(paths)

  os.chdir(path)

  window = tk.Tk()

  window.title(text["claimPrinter"])

  window.geometry('800x800')

  fromDateLabel = tk.Label(window, text=text['fromDate'])
  fromDate = tk.Text(window, width=80, height=1)
  toDateLabel = tk.Label(window, text=text['toDate'])
  toDate = tk.Text(window, width=80, height=1)
  barcodeLabel = tk.Label(window, text=text['barcode'])
  barcode = tk.StringVar(window, 0)
  b1 = tk.Radiobutton(window, text=text['all'], variable = barcode, value = 0)
  b2 = tk.Radiobutton(window, text=text['HK0'], variable = barcode, value = 1)
  b3 = tk.Radiobutton(window, text=text['HK1'], variable = barcode, value = 2)
  b4 = tk.Radiobutton(window, text=text['HK5'], variable = barcode, value = 3)

  categoryLabel = tk.Label(window, text=text['category'])
  category = tk.StringVar(window, 0)
  c0 = tk.Radiobutton(window, text=text['all'], variable = category, value = 0)
  c1 = tk.Radiobutton(window, text=text['2xx'], variable = category, value = 1)
  c2 = tk.Radiobutton(window, text=text['8xx'], variable = category, value = 2)
  c3 = tk.Radiobutton(window, text=text['others'], variable = category, value = 3)

  sheet= tksheet.Sheet(window, width=800, height=600)
  fileName = tk.Label(window, text='FileName')

  search = tk.Button(window, text=text["search"])
  generate = tk.Button(window, text=text["generate"])

  search["state"] = "disabled"
  generate["state"] = "disabled"

  password = Config['password']
  connection = Config['connection'].format(password)
  books = dict()
  claimBuilder = None

  def loadingThread(connection):
    global books
    global claimBuilder
    print(f"Load Book DB {connection}")
    try:
        client = MongoClient(connection)
        db = client.library
        print("Read books")
        books = convertToSQL(db.book, "BARCODE", sqlBookDict)
    except Exception as e:
        print(f"Exception {e}")

    print(f"Loaded {len(books)} books")
    claimBuilder = ClaimBuilder(books)
    search["state"] = "normal"
    generate["state"] = "normal"


  loading = threading.Thread(target = loadingThread, args = (connection,))
  loading.start()

  print("Open MongoDB")
  showBooks = list()

  def searchBooks(args):
    global showBooks
    filters = dict()
    print("Search")
    fromDateStr = fromDate.get('0.0', tk.END).replace("\n", "")
    toDateStr = toDate.get('0.0', tk.END).replace("\n", "")
    print(f"{fromDateStr} ~ {toDateStr}")
    print(barcode.get())
    print(type(barcode.get()))
    print(type(category.get()))
    barcodeNum = int(barcode.get())
    categoryNum = int(category.get())
    if len(fromDateStr) > 0:
        filters["fromDate"] = fromDateStr
    if len(toDateStr) > 0:
        filters["toDate"] = toDateStr
    barcodeStr = ["", "HK0", "HK1", "HK5"]
    categoryStr = ["", "2", "8", "OTHER"]
    if barcodeNum != 0:
        filters["barcode"] = barcodeStr[barcodeNum]
    if categoryNum != 0:
        filters["category"] = categoryStr[categoryNum]
    print(filters)

    showBooks = claimBuilder.getList(filters)
    print(len(showBooks))
    bookList = list()
    for entry in showBooks:
        book = list()
        book.append(entry["BARCODE"])
        book.append(entry["BOOKNAME"])
        book.append(entry["CLAIM"])
        book.append(entry["REG_DATE"])
        bookList.append(book)
    sheet.set_sheet_data(bookList)

  def generateClaims(args):
    filename = 'file://' + os.getcwd() + "/" + 'claim.html'
    fileName.config(text = f"Generate claim {filename} vs {__file__}")
    global showBooks
    try:
        print(f"Generate {len(showBooks)} books")
        claimBuilder.generateHtml(showBooks, "claim.html")
        fileName.config(text = filename)
        webbrowser.open_new_tab(filename)
    except Exception as e:
        fileName.config(text = f"Failed to open: {e}")

  search.bind("<Button-1>", searchBooks)
  generate.bind("<Button-1>", generateClaims)

  fromDateLabel.grid(column=0, row=0)
  fromDate.grid(column=1, row=0, columnspan=4)
  toDateLabel.grid(column=0, row=1)
  toDate.grid(column=1, row=1, columnspan=4)
  barcodeLabel.grid(column=0, row=2)
  b1.grid(column=1, row=2)
  b2.grid(column=2, row=2)
  b3.grid(column=3, row=2)
  b4.grid(column=4, row=2)
  categoryLabel.grid(column=0, row=3)
  c0.grid(column=1, row=3)
  c1.grid(column=2, row=3)
  c2.grid(column=3, row=3)
  c3.grid(column=4, row=3)

  search.grid(column=0, row=4)
  generate.grid(column=1, row=4)

  fileName.grid(row=5, column=0, columnspan=5)

  sheet.grid(row=6, column=0, columnspan=5)
  sheet.headers([text["barcode"], text["bookName"], text["claim"], text["regDate"]])


  window.mainloop()
