#!/bin/python3

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
from Text import text, getText
from marc import MARC

def setText(widget, text):
    widget.delete("0.0", tk.END)
    widget.insert(tk.END, text)

def readText(widget):
    return widget.get('0.0', tk.END).strip()

def resize(event):
    pass
#    print("Configure changed")
#    print(event)

class BookInfo:
    def __init__(self, connection, window):
        self.win = window
        self.selectedRow = 0
        self.books = dict()
        self.pop = None
        self.infoText = ['Barcode', 'ISBN', 'TotalName', 'BookName', 'ExCate', 'Author', 'Category', 'Publish', 'AuthorCode', 'BookNum', 'ClaimNum', 'CopyNum', 'Claim', "Delete"]
        self.infoKey = ["_id", "isbn", "series", "title", "ex_cate", "author", "category", "publisher", "author_code", "num", "claim_num", "copy_num", "claim", "deleted"]
        self.labels = list()
        self.texts = list()

        self.client = MongoClient(connection)
        self.db = self.client.library

        loading = threading.Thread(target = self.loadingThread, args = (connection,))
        loading.start()


    def registerWidgets(self):
        for rowIdx in range(len(self.infoText)):
            label = tk.Label(self.win, text=getText(self.infoText[rowIdx]))
            label.grid(column=0, row=rowIdx)
            self.labels.append(label)
            text = tk.Text(self.win, width=50, height=2)
            text.grid(column=1, row=rowIdx, columnspan=2)
            text.bind("<KeyRelease>", self.checkTextChange)
            self.texts.append(text)
        self.saveButton = tk.Button(self.win, text=getText("save"), width=20)
        self.saveButton.grid(column=1, row=len(self.texts))
        self.saveButton["state"] = "disabled"
        self.resetButton = tk.Button(self.win, text=getText("reset"), width=20)
        self.resetButton.grid(column=2, row=len(self.texts))
        self.saveButton.bind("<Button-1>", self.save)
        self.resetButton.bind("<Button-1>", self.reset)
        search["state"] = "disabled"

    def selectBook(self, bookId):
        print(f"Set BookId {bookId}")
        book = self.books[bookId]
        print(book)
        seq = book["seqnum"]
        print(self.marcs[seq]["MARC_DATA"])
        self.bookData = list()
        for idx in range(len(self.texts)):
            self.bookData.append(book[self.infoKey[idx]])
            setText(self.texts[idx], self.bookData[idx])
        self.checkTextChange(None)

    def disable_event(self):
        pass

    def save(self, event):
        print(f"Save {self.saveButton['state']}")
        if self.pop or self.saveButton["state"] != "normal":
            return
        self.pop = tk.Toplevel(self.win)
        self.pop.title(getText("Save"))
        self.pop.geometry("300x150")
        self.pop.protocol("WM_DELETE_WINDOW", self.disable_event)
        label = tk.Label(self.pop, text="Confirm")
        label.pack(pady=20)
        frame = tk.Frame(self.pop, bg="#808080")
        frame.pack(pady=10)
        button1 = tk.Button(frame, text="Yes", width=10, command=self.confirmedSave)
        button1.grid(row=0, column=1)
        button2 = tk.Button(frame, text="No", width=10, command=self.cancel)
        button2.grid(row=0, column=2)

    def confirmedSave(self):
        if self.pop:
            self.pop.destroy()
            self.pop = None
        print("Save confirmed")
        for idx in range(len(self.texts)):
            textWidget = self.texts[idx]
            self.bookData[idx] = readText(textWidget)
        print(self.bookData)
        key = self.bookData[0]
        print(self.books[key])
        book = self.books[key]
        for idx in range(len(self.bookData)):
            book[self.infoKey[idx]] = self.bookData[idx]
        print(book)
        seq = book["seqnum"]
        print(f"Before: {self.marcs[seq]}")
        marc = MARC(self.marcs[seq]["MARC_DATA"])
        marc.decode()
        marc.setBookInfo(convertEntryToSQL(book, sqlBookDict))
        self.marcs[seq]["MARC_DATA"] = marc.encode()
        self.marcs[seq]["DELETE_YN"] = book["deleted"]
        print(f"After:  {self.marcs[seq]}")

        updates = [list(), [key], list()]
        print(updates)
        updateCloud(updates, self.books, self.db.book)

        updates = [list(), [seq], list()]
        print(updates)
        updateCloud(updates, self.marcs, self.db.marc)


    def cancel(self):
        if self.pop:
            self.pop.destroy()
            self.pop = None

    def reset(self, event):
        for idx in range(len(self.texts)):
            setText(self.texts[idx], self.bookData[idx])

    def searchBook(self, keyword):
        ret = list()
        keyword = keyword.lower()
        for key in self.books:
            book = self.books[key]
            if ( keyword in book["title"].lower() or
                 keyword in book["series"].lower() or
                 keyword in book["author"].lower()):
                ret.append(book)
        return ret

    def checkTextChange(self, event):
        changed = False
        for idx in range(len(self.texts)):
            text = self.texts[idx]
            value = text.get('0.0', tk.END).strip()
#            print(f"[{self.bookData[idx]}]")
#            print(f"[{value}]")
            if self.bookData[idx] != value:
                changed = True
                text.tag_add("all", "0.0", tk.END)
                text.tag_config("all", background="#ffc0c0")
            else:
                text.tag_add("all", "0.0", tk.END)
                text.tag_config("all", background="#ffffff")
        print(changed)
        if changed:
            self.saveButton["state"] = "normal"
        else:
            self.saveButton["state"] = "disabled"


    def loadingThread(self, connection):
        print(f"Load Book DB {connection}")
        try:
            print("Read books")
            self.books = mdb2dict(self.db.book)
            print("Read marcs")
            self.marcs = mdb2dict(self.db.marc)
        except Exception as e:
            print(f"Exception {e}")

        print(f"Loaded {len(self.books)} books")
        search["state"] = "normal"


if __name__ == '__main__':
  path = __file__

  if "/" in path:
    delimiter = "/"
  else:
    delimiter = "\\"
  paths = path.split(delimiter)[0:-1]
  path = "/".join(paths)

  os.chdir(path)

  password = Config['password']
  connection = Config['connection'].format(password)

  window = tk.Tk()

  window.title(getText("Book Editor"))

  window.geometry('1500x800')

  window.bind("<Configure>", resize)

  leftFrame = tk.Frame(window, width = 500)
  rightFrame = tk.Frame(window, width = 500)
  leftFrame.grid(column=0, row=0)
  rightFrame.grid(column=1, row=0)

  bookInfo = BookInfo(connection, rightFrame)

  keywordLabel = tk.Label(leftFrame, text=getText('keyword'))
  keywordText = tk.Text(leftFrame, width=80, height=2)

  sheet = tksheet.Sheet(leftFrame, width=800, height=600, column_width=150)

  search = tk.Button(leftFrame, text=text["search"])

  bookInfo.registerWidgets()


  search["state"] = "disabled"

  print("Open MongoDB")

  def searchBooks(args):

    filters = dict()
    print("Search")
    keyword = keywordText.get('0.0', tk.END).strip()
    showBooks = bookInfo.searchBook(keyword)

    print(len(showBooks))
    bookList = list()
    for entry in showBooks:
        book = list()
        book.append(entry["_id"])
        book.append(entry["title"])
        book.append(entry["claim"])
        book.append(entry["registration_date"])
        bookList.append(book)
    sheet.set_sheet_data(bookList)

  search.bind("<Button-1>", searchBooks)

  keywordLabel.grid(column=0, row=0)
  keywordText.grid(column=1, row=0, columnspan=4)
  search.grid(column=0, row=4)

  def clickSheet(event):
    print("Click sheet")
    row = sheet.identify_row(event)
    print(row)
    selectBook(row)

  def keyDownSheet(event):
    print(event.keysym)
    row = bookInfo.selectedRow
    if event.keysym == "Up":
        row -= 1
    if event.keysym == "Down":
        row += 1
    selectBook(row)

  def selectBook(row):
    if type(row) == None or row < 0 or row >= len(sheet.get_sheet_data()):
        return
    bottom = False
    if bookInfo.selectedRow < row:
        bottom = True
    sheet.see(row = row, bottom_right_corner = bottom)
    bookInfo.selectedRow = row
    sheet.dehighlight_all()
    sheet.highlight_rows(rows=[row], bg="#8080ff")
    bookId = sheet.get_cell_data(row, 0)
    print(bookId)
    bookInfo.selectBook(bookId)

  sheet.grid(row=6, column=0, columnspan=5, rowspan=6, sticky="news")
  sheet.headers([text["barcode"], text["bookName"], text["claim"], text["regDate"]])
  sheet.bind("<ButtonPress-1>", clickSheet)
  sheet.bind("<KeyPress>", keyDownSheet)
#  sheet.set_option(auto_resize_columns)


  window.mainloop()
