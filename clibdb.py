import pyodbc

class CLibDB():
    def __init__(self):
        self.connection = pyodbc.connect(
            'Driver={SQL Server Native Client 11.0};'
            'Server=(localdb)\\v11.0;'
            'AttachDbFileName=C:\CLIB\Data\CLIB.mdf;'
#            'AttachDbFileName=./CLIB.mdf'
            'integrated security = true')
        self.connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
        self.connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16le')
#        self.connection.setencoding(encoding='utf-8')
#        self.connection.setencoding(encoding='euc-kr')

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
