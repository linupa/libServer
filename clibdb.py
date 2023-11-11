import pyodbc
from sys import platform

class CLibDB():
    def __init__(self):
        pyodbc.pooling = False
        if platform == "linux":
            dbPath = "/mnt/c/CLIB/Data/CLIB.mdf"
        else:
            dbPath = "C:\CLIB\Data\CLIB.mdf"
        drivers = pyodbc.drivers()
        driver = drivers[-1]
        self.connection = pyodbc.connect(
            'Driver={' + driver + '};'
            'Server=(localdb)\\v11.0;'
            'AttachDbFileName=' + dbPath + ';'
            'integrated security = true')
        self.connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
        self.connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16le')
        self.connection.setencoding(encoding='utf-16le', ctype=pyodbc.SQL_WCHAR)

        cursor = self.connection.cursor()
#        for row in cursor.tables():
#            print(row.table_name)

    def RunQuery(self, query):
        cursor = self.connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def UpdateQuery(self, query):
        cursor = self.connection.cursor()
        cursor.execute(query)
        self.connection.commit()
        cursor.close()

    def UpdateQueryWithValue(self, query, params):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        cursor.close()

    def close(self):
        cursor = self.connection.cursor()
        cursor.close()
        self.connection.close()
