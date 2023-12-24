import tkinter as tk
from tkinter import ttk

class Progress:
    def __init__(self, window, name):
        self.window = window
        self.bookLabel = tk.Label(window, text=name)
        self.bookProgress = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
        self.bookLabel2 = tk.Label(window, text=name)
        self.bookUpdate = ttk.Progressbar(window, orient="horizontal", mode="determinate", length=600)
        self.bookState = tk.Label(window, text="")
        self.count = 1

    def setCount(self, count):
        self.count = count

    def addDownload(self, index):
        self.bookLabel.grid(column = 0, row = index)
        self.bookProgress.grid(column = 1, row = index)

    def addUpdate(self, index):
        self.bookLabel2.grid(column = 0, row = index)
        self.bookUpdate.grid(column = 1, row = index)
        self.bookState.grid(column = 1, row = index+1)

    def setDownload(self, value):
        self.bookProgress["value"] = 100 * value / self.count

    def setUpdate(self, value):
        self.bookUpdate["value"] = value

    def setState(self, state):
        self.bookState.config(text = state)

