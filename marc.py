from Text import text
from collections import OrderedDict
from datetime import datetime

#ENCODING = 'euc-kr'
ENCODING = 'cp949'
#ENCODING = 'utf-8'
BEGIN = "\x1f"
END = "\x1e"
begin = "\r"
end = "\n"

class Field:
    def __init__(self, tag, encoded = None):
        self.tag = tag
        if encoded == None:
            return
        decoded = encoded.decode(ENCODING)
        if tag in {"005", "008"}:
            self.data = decoded[0:-1]
        else:
            self.indicator = decoded[0:2]
            self.subfields = OrderedDict()
            key = None
            item = ""
            entries = list()
            idx = 0
            while idx < len(decoded):
                c = decoded[idx]
                if c == begin:
                    if key:
                        self.subfields[key] = item
                    idx +=1
                    key = decoded[idx]
                    item = ""
                elif c == end:
                    if key:
                        self.subfields[key] = item
                    break
                else:
                    item += c

                idx += 1

    def encode(self):
        fieldStr = str()
        encoded = str()
        if self.tag in {"005", "008"}:
            fieldStr += self.data
        else:
            fieldStr += self.indicator
            for key in self.subfields:
                fieldStr += begin + key + self.subfields[key]
        fieldStr += end
        encodedField = bytes(fieldStr, ENCODING)
        encoded += fieldStr
        size = len(encodedField)
        return size, encoded

    def __str__(self):
        ret = str()
        ret += f"{self.tag}: "
        if self.tag in {"005", "008"}:
            ret += f"[{self.data}]"
        else:
            ret += f"[{self.indicator}]: "
            subfields = list()
            for key in self.subfields:
                subfields.append(f"{key}: {self.subfields[key]}")
            ret += ", ".join(subfields)
        return ret

    def __repr__(self):
        return self.__str__()

class MARC:
    def __init__(self, marcString, debug = False):
        if debug:
            print(marcString)
        self.orgString = marcString
        self.debug = debug
        self.marc = marcString.replace(begin, "").replace(end, "")
        self.marc = self.marc.replace("\x1d", "").replace(BEGIN, begin).replace(END, end)
        self.marc = self.marc.replace("\xa1\xea", "").replace("\xa1\xe3", "\r").replace("\xa1\xe5", "\n")
        self.marc = self.marc.replace("↔", "").replace("▲", end).replace("▼", begin)
        if self.debug:
            print(bytes(self.marc, ENCODING))
            print(self.marc)


    def decode(self):
        encoded = bytes()
        for c in self.marc:
            try:
                encoded += bytes(c, ENCODING)
            except Exception as e:
                encoded += bytes(" ", ENCODING)
        if self.debug:
            print("=" * 10 + " Decode")
            print(len(encoded))
        self.header = encoded[0:24].decode(ENCODING)
        encoded = encoded[24:]
        for i in range(len(encoded)):
            if encoded[i] == 0x0a: # 0x25: # "%"
                break
        directory = encoded[:i].decode(ENCODING)
        encoded = encoded[i+1:]
        idx = 0
        last = 0
        if self.debug:
            print(directory)
        self.rawDirectory = directory
        self.directory = list()
        while len(directory):
            key = directory[0:3]
            size = directory[3:7]
            offset = directory[7:12]
            directory = directory[12:]
            if self.debug:
                print(f"{key}: {offset} + {size}")
            self.directory.append((key, offset, size))
        self.rawFields = encoded.decode(ENCODING)
        fieldIdx = 0
        self.fields = list()

        for (key, offset, size) in self.directory:
            fromIdx = int(offset)
            toIdx = fromIdx + int(size)
            data = encoded[fromIdx:toIdx]
            field = Field(key, data)
            self.fields.append(field)
            if key == "005":
                if self.debug:
                    print(f"Timestamp: {field.data}")
                self.timestamp = field.data


    def encode(self, changeDate = False):

        timestampField = self.findField("005")
        timestampField.data = self.timestamp

        fieldStr = str()
        sizes = list()
        for field in self.fields:
            size, string = field.encode()
            fieldStr += string
            sizes.append(size)
        if self.debug:
            print("=" * 10 + " Field compare")
            print("1: " + fieldStr.replace("\r", ", "))
            print("2: " + self.rawFields.replace("\r", ", "))
            print(fieldStr == self.rawFields)
            print(sizes)

        directory = ""
        offset = 0
        for i in range(len(sizes)):
            directory += self.fields[i].tag
            directory += f"{sizes[i]:04}"
            directory += f"{offset:05}"
            offset += sizes[i]
        if self.debug:
            print(f"[{directory}]")
            print(f"[{self.rawDirectory}]")

        marc = self.header + directory + end + fieldStr
        midLength = len(self.header + directory + end)
        length = midLength + len(bytes(fieldStr, ENCODING)) + 1

        if self.debug:
            print("Compare:")
            print("-" * 80)
            print(marc.replace("\r", ", "))
            print("-" * 80)
            print(self.marc.replace("\r", ", "))
            print("-" * 80)
            print(f"Length: {length}")
            print(f"MidLength: {midLength}")

        marcStr =  f"{length:05d}" + marc[5:12] + f"{midLength:05d}" + marc[17:]
        marcStr = marcStr.replace(begin, BEGIN).replace(end, END)
        marcStr += "\x1d"

        return marcStr

    def findField(self, tag):
        for entry in self.fields:
            if entry.tag == tag:
                return entry
        else:
            return None

    def setValue(self, tag, key, value):
        field = self.findField(tag)
        if not field:
            field = Field(tag)
            field.indicator = "  "
            field.subfields = OrderedDict()
            self.fields.append(field)
        field.subfields[key] = value

    def getValue(self, field, value, default = ""):
        field = self.findField(field)
        if field and value in field.subfields:
            value = field.subfields[value]
        else:
            value = default
        return value.strip()

    def check(self):
        field = self.findField("049").subfields
        if "HK0" not in field["l"]:
            return
        if "f" not in field or field["f"] != text["kid"]:
            print("Has no KID")
#            print(self.marc)
            field["f"] = text["kid"]

    def getBookInfo(self):
        info = dict()
        y = self.timestamp[0:4]
        m = self.timestamp[4:6]
        d = self.timestamp[6:8]
        H = self.timestamp[8:10]
        M = self.timestamp[10:12]
        S = self.timestamp[12:14]
        timestamp = f"{y}-{m}-{d}, {H}:{M}:{S}"
        info["MOD_DATE"] = timestamp

        info["BARCODE"] = self.getValue("049", "l")
        info["EX_CATE"] = self.getValue("049", "f")
        info["ISBN"] = self.getValue("020", "a")
        info["BOOKNAME"] = self.getValue("245", "a")
        info["BOOKNUM"] = self.getValue("245", "n")
        info["AUTHOR"] = self.getValue("245", "d")

        info["CATEGORY"] = self.getValue("056", "a")
        info["PUBLISH"] = self.getValue("260", "b")
        info["TOTAL_NAME"] = self.getValue("440", "a")
        info["AUTHOR_CODE"] = self.getValue("090", "b")
        info["CLAIMNUM"] = self.getValue("090", "c")
        info["COPYNUM"] = self.getValue("049", "c")

        info["CLAIM"] = "_".join((info["EX_CATE"], info["CATEGORY"], info["AUTHOR_CODE"], info["CLAIMNUM"], info["COPYNUM"])).strip()

        return info

    def setValueHelper(self, field, key, info, infoKey):
        if infoKey not in info:
            return
        self.setValue(field, key, info[infoKey])


    def setBookInfo(self, info):
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        print(f"Update book info at {now}")
        self.timestamp = now

        self.setValueHelper("020", "a", info, "ISBN")

        self.setValueHelper("049", "c", info, "COPYNUM")
        self.setValueHelper("049", "f", info, "EX_CATE")
        self.setValueHelper("049", "l", info, "BARCODE")
        self.setValueHelper("049", "v", info, "CLAIMNUM")

        self.setValueHelper("056", "a", info, "CATEGORY")

        self.setValueHelper("090", "a", info, "CATEGORY")
        self.setValueHelper("090", "b", info, "AUTHOR_CODE")
        self.setValueHelper("090", "c", info, "CLAIMNUM")

        self.setValueHelper("100", "a", info, "AUTHOR")

        self.setValueHelper("245", "a", info, "BOOKNAME")
        self.setValueHelper("245", "d", info, "AUTHOR")
        self.setValueHelper("245", "n", info, "BOOKNUM")

        self.setValueHelper("260", "b", info, "PUBLISH")

        self.setValueHelper("440", "a", info, "TOTAL_NAME")

        print(self.fields)


