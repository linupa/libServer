from Text import text

#ENCODING = 'euc-kr'
ENCODING = 'cp949'
#ENCODING = 'utf-8'
BEGIN = "\x1f"
END = "\x1e"
begin = "\r"
end = "\n"

class MARC:
    def __init__(self, marcString, debug = False):
        if debug:
            print(marcString)
        self.debug = debug
        self.marc = marcString.replace(begin, "").replace(end, "")
        self.marc = self.marc.replace("\x1d", "").replace(BEGIN, begin).replace(END, end)
        self.marc = self.marc.replace("\xa1\xea", "").replace("\xa1\xe3", "\r").replace("\xa1\xe5", "\n")
        self.marc = self.marc.replace("↔", "").replace("▲", end).replace("▼", begin)
        if self.debug:
            print(bytes(self.marc, ENCODING))
            print(self.marc)


    def decodeGroup(self, group):
        code = group[0:2]
        data = group[2:]
        idx = 0
        items = dict()
        key = None
        item = ""
        entries = list()
        while idx < len(data):
            c = data[idx]
            if c == begin:
                if key:
                    items[key] = item
                idx +=1
                key = data[idx]
                item = ""
            elif c == end:
                if key:
                    items[key] = item
                break
            else:
                item += c

            idx += 1
        entries.append(code)
        if len(items) > 0:
            entries.append(items)
        else:
            entries.append(data[0:-1])
        return entries

    def encodeGroup(self):
        sizes = list()
        encoded = ""
        if self.debug:
            print(self.groups)
        for group in self.groups:
            groupStr = group[1]
            if type(group[2]) == str:
                groupStr += group[2]
            else:
                for key in group[2]:
                    groupStr += begin + key + group[2][key]
            groupStr += end
            encodedGroup = bytes(groupStr, ENCODING)
            encoded += groupStr
            sizes.append(len(encodedGroup))
        return sizes, encoded

    def decode(self):
        encoded = bytes()
        for c in self.marc:
            try:
                encoded += bytes(c, ENCODING)
            except Exception as e:
                encoded += bytes(" ", ENCODING)
        if self.debug:
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
        self.rawGroups = encoded.decode(ENCODING)
        groupIdx = 0
        self.groups = list()
        while idx < len(encoded):
            for last in range(idx, len(encoded)):
                if encoded[last] == 0x0a: # 0x25: # "%"
                    break
            entry = encoded[idx:last+1]
            group = [self.directory[groupIdx][0]] + self.decodeGroup(entry.decode(ENCODING))
            self.groups.append(group)
            if self.debug:
                print(f"{idx}: {len(entry)}: {group}")
            idx = last + 1
            groupIdx += 1

    def encode(self):

        sizes, encodedGroups = self.encodeGroup()
        if self.debug:
            print(sizes)
        groupStr = encodedGroups
        if self.debug:
            print(groupStr)
            print(self.rawGroups)
            print(groupStr == self.rawGroups)
        directory = ""
        offset = 0
        for i in range(len(sizes)):
            directory += self.groups[i][0]
            directory += f"{sizes[i]:04}"
            directory += f"{offset:05}"
            offset += sizes[i]
        if self.debug:
            print(directory)
            print(self.rawDirectory)

        marc = self.header + directory + end + encodedGroups

        if self.debug:
            print(marc)
            print(self.marc)

        marcStr =  marc
        marcStr = marcStr.replace(begin, BEGIN).replace(end, END)
        marcStr += "\x1d"

        return marcStr

    def findGroup(self, group):
        for entry in self.groups:
            if entry[0] == group:
                return entry
        else:
            return None

    def getValue(self, group, value, default = ""):
        group = self.findGroup(group)
        if group and value in group[2]:
            value = group[2][value]
        else:
            value = default
        return value.strip()

    def check(self):
        group = self.findGroup("049")[2]
        if "HK0" not in group["l"]:
            return
        if "f" not in group or group["f"] != text["kid"]:
            print("Has no KID")
#            print(self.marc)
            group["f"] = text["kid"]

    def getBookInfo(self):
        info = dict()
        info["BARCODE"] = self.getValue("049", "l")
        info["EX_CATE"] = self.getValue("049", "f")
        info["ISBN"] = self.getValue("020", "a")
        info["AUTHOR"] = self.getValue("245", "d")

        info["CATEGORY"] = self.getValue("056", "a")
        info["PUBLISH"] = self.getValue("260", "b")
        info["TOTAL_NAME"] = self.getValue("440", "a")
        info["AUTHOR_CODE"] = self.getValue("090", "b")
        info["CLAIMNUM"] = self.getValue("090", "c")
        info["COPYNUM"] = self.getValue("049", "c")

        info["CLAIM"] = "_".join((info["EX_CATE"], info["CATEGORY"], info["AUTHOR_CODE"], info["CLAIMNUM"], info["COPYNUM"])).strip()

        return info


