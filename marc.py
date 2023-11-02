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
        self.numBytes = 0
        self.numUni = 0
        self.marc = marcString.replace(begin, "").replace(end, "")
        self.marc = self.marc.replace("\x1d", "").replace(BEGIN, begin).replace(END, end)
        self.marc = self.marc.replace("\xa1\xea", "").replace("\xa1\xe3", "\r").replace("\xa1\xe5", "\n")
        self.marc = self.marc.replace("↔", "").replace("▲", end).replace("▼", begin)
        marcLen = 0
        if self.debug:
            print(bytes(self.marc, ENCODING))
#            print(f"euc-kr length: {len(bytes(self.marc, ENCODING))}")
            print(self.marc)
        for c in self.marc:
            try:
                clen = len(bytes(c, ENCODING))
            except Exception as e:
                clen = 2

            if clen > 1:
                self.numUni += 1
                self.numBytes += 2
            else:
                self.numBytes += 1
            marcLen += clen
        if self.debug:
            print(marcLen)
        self.header = self.marc[0:24]

        for i in range(len(self.marc) - 24):
            if self.marc[i + 24] == end:
                break
        directory = self.marc[24:24+i]
        numDir = int(i / 12)
        idx = 24
        self.entries = list()
        for i in range(numDir):
            f1 = self.marc[idx:idx+3]
            idx += 3
            f2 = int(self.marc[idx:idx+4])
            idx += 4
            f3 = int(self.marc[idx:idx+5])
            idx += 5
            if self.debug:
                print(f"{f1} {f2} {f3}")
            self.entries.append([f1, f2, f3])

        data = self.marc[idx+1:]
        startIdx = 0
        dataEntries = list()
        for i in range(len(data)):
            if data[i] == end:
               dataEntries.append(data[startIdx:i + 1])
               startIdx = i + 1
        #print(dataEntries)
        if self.debug:
            print(f"Directory: {directory}")
            print(dataEntries)
            print(len(self.entries))

        self.entries = list()
        for i in range(len(self.entries)):
#            self.entries[i] = self.decodeGroup(dataEntries[i])
            self.entries.append(self.decodeGroup(dataEntries[i]))

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

    def check(self):
        group = self.findGroup("049")[2]
        if "HK0" not in group["l"]:
            return
        if "f" not in group or group["f"] != text["kid"]:
            print("Has no KID")
#            print(self.marc)
            group["f"] = text["kid"]


