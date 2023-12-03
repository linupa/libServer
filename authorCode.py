bIndex = [0, 1, 3, 6, 7, 8, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
eIndex = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23, 25, 26, 27, 28, 29]

bValue = [1, 1, 19, 2, 2, 29, 3, 4, 4, 5, 5, 6, 7, 7, 8, 87, 88, 89, 9]
mValue1 = [2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 7, 7, 8]
mValue2 = [2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 6]
bOffset = 12593
mOffset = 12623

def dissemble(ch):
    num = ord(ch) - 44032
    if num < 0:
        return None
    c1 = int(num / 588)
    temp = (num % 588)
    c2 = int(temp / 28)
    c3 = temp % 28
    return (c1, c2, c3)

def getAuthorCode(name, book = None):
    if len(name) < 2:
        return(name)
    bookCode = ""
    try:
        code = name[0]
        dis = dissemble(name[1])
        if dis:
            value = str(bValue[dis[0]])
            if dis[0] == 14:
                value += str(mValue2[dis[1]])
            else:
                value += str(mValue1[dis[1]])
            code += str(value)
        if book and len(book) > 0:
            dis = dissemble(book[0])
            if dis:
                bookCode = chr(12593 + bIndex[dis[0]])
                code += bookCode
    except Exception as e:
        print("Failed to get author code")
        print(dis)



    return code


if __name__ == "__main__":
    ks1 = '가'
    ns1 = ord(ks1)
    ks2 = '나'
    ns2 = ord(ks2)

    print(ns1)
    print(ns2)
    gap = ns2 - ns1

    print(chr(ns2+gap))

    s = "김린서"
    for i in range(20):
        print(chr(44592-28*20+i*588), end="")
    print("")
    for c in s:
        print(f"{ord(c):x}")
        print(dissemble(c))
    print(getAuthorCode(s))

    for i in range(19):
        print(chr(44592-28*20+i*588), end="")
    print("")
    for b in bIndex:
        print(chr(12593+b), end="")
    print("")
    for i in range(28):
        print(chr(12593+i), end="")
    print("")
    print("???")
    for e in eIndex:
        print(chr(12593+e), end="")
    print("")
    for i in range(28):
        print(chr(44592-28*20+i+1), end="")
    print("")
    for i in range(21):
        print(chr(44592-28*20+i*28), end="")
    print("")
    for i in range(21):
        print(chr(12623+i), end="")
    print("")

