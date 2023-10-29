class MARC:
    def __init__(self, marcString):
        self.numBytes = 0
        self.numUni = 0
        self.marc = marcString.replace("\x1d", "").replace("\x1e", "%").replace("\x1f", "$")
        for c in self.marc:
            clen = len(bytes(c, 'utf-8'))
            if clen > 1:
                self.numUni += 1
                self.numBytes += 2
            else:
                self.numBytes += 1
        self.header = self.marc[0:24]

        for i in range(len(self.marc) - 24):
            if self.marc[i + 24] == "%":
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
        #    print(f"{f1} {f2} {f3}")
            self.entries.append([f1, f2, f3])

        data = self.marc[idx+1:]
        startIdx = 0
        dataEntries = list()
        for i in range(len(data)):
            if data[i] == "%":
               dataEntries.append(data[startIdx:i + 1])
               startIdx = i + 1
        #print(dataEntries)


        for i in range(len(self.entries)):
            code = dataEntries[i][0:2]
            data = dataEntries[i][2:]
            idx = 0
            items = dict()
            key = None
            item = ""
            while idx < len(data):
                c = data[idx]
                if c == "$":
                    if key:
                        items[key] = item
                    idx +=1
                    key = data[idx]
                    item = ""
                elif c == "%":
                    if key:
                        items[key] = item
                    break
                else:
                    item += c

                idx += 1
            self.entries[i].append(code)
            if len(items) > 0:
                self.entries[i].append(items)
            else:
                self.entries[i].append(data)
