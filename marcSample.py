from marc import MARC

sample = '00497namk   00169 k 4500005001500000008004100015020002000056049002800076056001000104090001800114100005300132245007400185260002500259300001800284440002000302950000500322\x1e20180503123131\x1e170115s2001    ulka          000a  kor  \x1e  \x1fa9788939511712\x1fc\x1e0 \x1flHK00000027\x1fc \x1ff아동\x1fv20\x1e  \x1fa808.9\x1e  \x1fa808.9\x1fb아\x1fc20\x1e1 \x1fa이치카와 노부코 글, 야부키 노부히코 그림, 김증래\x1e00\x1fa공룡이 나타나다\x1fd이치카와 노부 코 글, 야부키 노부히코 그림, 김증래\x1fn72\x1e  \x1fa서울\x1fb대교출판\x1fc2001\x1e  \x1fa32p.\x1fc27cm\x1fe \x1e00\x1fa아이들의 벗\x1fv20\x1e0 \x1fb\x1e\x1d'

if __name__  == "__main__":

    marc = MARC(sample)
    #print(self.marc)
    print(f"Header: {marc.header}")
    #print(f"Direct: {directory}")
    #print(len(directory))
    #print(f"Data  : {data}")
    for entry in marc.entries:
        print(entry)
    print(len(marc.marc))
    print(marc.numBytes)
    print(marc.numUni)
