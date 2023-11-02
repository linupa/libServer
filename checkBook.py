from pymongo import MongoClient
from config import Config
from clibrary import CLibrary
from dbUtil import *
from marc import MARC

import dns.resolver
dns.resolver.default_resolver=dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers=['8.8.8.8']

password = Config['password']
connection = Config['connection'].format(password)

def checkBook(mongoDb):
    print("Check book DB")

    print("="*80)
    print("Book")
    books = mdb2dict(mongoDb.book)
    print(f"{len(books)} books")

    print("="*80)
    print("MARC")
    marcs = mdb2dict(mongoDb.marc)
    print(f"{len(marcs)} MARCs")

    print("="*80)
    print("Rent")
    rents = mdb2dict(mongoDb.rent)
    print(f"{len(rents)} rents")

    numDeleted = 0
    states = dict()
    for key in books:
        book = books[key]
        seqnum = book["seqnum"]
        if seqnum not in marcs:
            print(f"MARC for {key} is missing")
            print(book)
        if book['deleted'] in {"Y", "y"}:
            numDeleted += 1
            if key in rents:
                print(f"Deleted book has a state")
                print(book)
                print(rents[key])
        if seqnum in rents:
            state = rents[seqnum]['state']
#            print(f"{key}: {state}")
            if state in states:
                states[state] += 1
            else:
                states[state] = 1

    matchCount = 0
    mismatchCount = 0
    failCount = 0
    for key in marcs:
        orgMarc = marcs[key]["MARC_DATA"]
        try:
            marc = MARC(orgMarc, debug=False)
            marc.decode()
            marc.check()
            newMarc = marc.encode()
            if bytes(orgMarc, "UTF-8") != bytes(newMarc, "UTF-8"):
                mismatchCount += 1
            else:
                matchCount += 1
        except Exception as e:
            print(f"Failed to decode MARC {e}")
            print(orgMarc)
            failCount += 1
    print(f"Same {matchCount} / Change {mismatchCount} / Fail {failCount} / Total {len(marcs)}")

    numValid = len(books) - numDeleted
    numAvail = numValid
    for state in states:
        numAvail -= states[state]

    print(f"Avaiable {numAvail} / Valld {numValid} / All {len(books)} / Deleted {numDeleted}")
    print(states)

    for key in rents:
        print(rents[key])
        break

if __name__ == '__main__':
    # Open MongoDB
    print(connection)
    client = MongoClient(connection)
    mongoDb = client.library

    checkBook(mongoDb)


