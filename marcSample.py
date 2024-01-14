from marc import MARC

sample = '00497namk   00169 k 4500005001500000008004100015020002000056049002800076056001000104090001800114100005300132245007400185260002500259300001800284440002000302950000500322\x1e20180503123131\x1e170115s2001    ulka          000a  kor  \x1e  \x1fa9788939511712\x1fc\x1e0 \x1flHK00000027\x1fc \x1ff아동\x1fv20\x1e  \x1fa808.9\x1e  \x1fa808.9\x1fb아\x1fc20\x1e1 \x1fa이치카와 노부코 글, 야부키 노부히코 그림, 김증래\x1e00\x1fa공룡이 나타나다\x1fd이치카와 노부 코 글, 야부키 노부히코 그림, 김증래\x1fn72\x1e  \x1fa서울\x1fb대교출판\x1fc2001\x1e  \x1fa32p.\x1fc27cm\x1fe \x1e00\x1fa아이들의 벗\x1fv20\x1e0 \x1fb\x1e\x1d'

sample = '00497namk   00169 k 4500005001500000008004100015020002000056049002800076056001000104090001800114100005300132245007400185260002500259300001800284440002000302950000500322\x1e20180503123131\x1e170115s2001    ulka          000a  kor  \x1e  \x1fa9788939511712\x1fc\x1e0 \x1flHK00000027\x1fc \x1ff아동\x1fv20\x1e  \x1fa808.9\x1e  \x1fa808.9\x1fb아\x1fc20\x1e1 \x1fa이치카와 노부코 글, 야부키 노부히코 그림, 김증래\x1e00\x1fa공룡이 나타나다\x1fd이치카와 노부 코 글, 야부키 노부히코 그림, 김증래\x1fn72\x1e  \x1fa서울\x1fb대교출판\x1fc2001\x1e  \x1fa32p.\x1fc27cm\x1fe \x1e00\x1fa아이들의 벗\x1fv20\x1e0 \x1fb\x1e\x1d'

#sample = '00430namk   00157 k 4500005001500000008004100015020002500056049002100081056001100102090002300113100003000136245005200166260002500218300001900243950001000262\x1e20170223122158\x1e170223s2002    ulka          000a  kor  \x1e  \x1fa9788988822135\x1fc\\9000\x1e0 \x1flHK10001528\x1fc6\x1fv3\x1e  \x1fa234.81\x1e  \x1fa234.81\x1fb엘294ㅇ\x1fc3\x1e1 \x1fa엘런 에임스 저, 정성호 역\x1e00\x1fa예수님의 눈으로 3\x1fd엘런 에임스 저, 정성호 역\x1fn3\x1e  \x1fa서 울\x1fb크리스챤\x1fc2002\x1e  \x1fa335p.\x1fc23cm\x1fe \x1e0 \x1fb\\9000\x1e\x1d'
sample = "00385namk   00169 k 4500005001500000008004100015020002000056049002600076056001000102090001700112100003200129245004500161260002500206300001800231440001900249950000500268▲20180503123130▲170115s2001    ulka          000a or  ▲  ▼a97889395121▼c▲0 ▼lHK00000001▼c▼f아동▼v1▲  ▼a808.9▲  ▼a808.9▼b아▼c1▲1 ▼a하마다 게이코 글.그림, 정근▲00▼a내 동생▼d그림, 정근▼n72▲  ▼a서울▼b대교출판▼c2001▲  ▼a28p.▼c27cm▼e ▲00▼a아이들의 벗▼v1▲0 ▼b▲↔"


sample = "00385namk   00157 k 4500005001500000008004100015020002200056049001800078056000800096090001900104100001400123245003400137260002600171300002000197950001000217▲20231015113413▲231015s2003    ulka          000a  kor  ▲  ▼6361191▼c\9000▲0  K10004997▼c ▲  ▼a816▲  ▼a816▼b편78ㅅ▼c ▲1 ▼a편집부 편▲00▼a산천을 닮은 사람들▼d편집부 편▲  ▼a서울:▼b효형출2p.:▼c23cm▼e ▲0 ▼b\9000▲↔"

#sample = "00450namk   00157 k 4500005001500000008004100015020002600056049001800082056001300100090002400113100002000137245008400157260002000241300002000261950001100281▲20180503123236▲180225s        ulka        000a  kor  ▲  ▼a9788952745385▼c'12000▲0 ▼lHK00003409▼c ▲  ▼a984.9102▲  ▼a984.9102 ▲1 ▼a,이창수 글 사진▲00▼a원더랜드 여행기 = ,Wonderland traveler : lzaka's bicycle diary▼d,이창수 글 사진▲  ▼a서울▼사▲  ▼a249p.▼c,21cm▼e ▲0 ▼b'12000▲↔"

sample = "00583namk   00169 k 4500005001500000008004100015020002600056049002700082056001000109090002000119100003400139245005800173260003000231300001800261440012300279950001100402▲20180801150458▲180801s20    ulka          000a  kor  ▲  ▼a9788956720753▼c\11580▲0 ▼lHK00005936▼c ▼v3▼f아동▲  ▼a219.2▼b글295▼c3▲1 ▼a신화나라탐사회 글,노현열 그림▲00▼a올림포스에 사는 12신들▼d신화나라탐사회 글,노현열 그림▲  ▼a서울:▼b교연아카데미▼c20▼c31cm▼e ▲00▼a(명화로 보는 테마동화) 글로벌 그리스 로마 신화=,Global Greek & Rome myths,,천지창조와 올림포스에 얽힌 신비로운 신화▼v3\11580▲↔"
sample = '00583namk   00169 k 4500005001500000008004100015020002600056049002700082056001000109090002000119100003400139245005800173260003000231300001800261440012300279950001100402\x1e20180801150458\x1e180801s2006    ulka          000a  kor  \x1e  \x1fa9788956720753\x1fc\\11580\x1e0 \x1flHK00005936\x1fc \x1fv3\x1ff아동\x1e  \x1fa219.2\x1e  \x1fa219.2\x1fb글295\x1fc3\x1e1 \x1fa신화나라탐사회 글,노현열 그림\x1e00\x1fa올림포스에 사는 12신들\x1fd신화나라탐사회 글,노현열 그림\x1e  \x1fa서울:\x1fb교연아카데미\x1fc2006\x1e  \x1fa1책:\x1fc31cm\x1fe \x1e00\x1fa(명화로 보는 테마동화) 글로벌 그리스 로마 신화=,Global Greek & Rome myths,,천지창조와 올림포스에 얽힌 신비로운 신화\x1fv3\x1e0 \x1fb\\11580\x1e\x1d'
sample = '00429namk   00157 k 4500005001500000008004100015020002600056049002200082056000800104090002000112100001600132245006400148260002600212300002200238950001100260\x1e20231231171044\x1e231231s2019    ulka          000a  kor  \x1e  \x1fa9788989749998\x1fc\\10000\x1e0 \x1flHK10005023\x1fc \x1fv10\x1e  \x1fa912\x1e  \x1fa912\x1fb고66ㅅ\x1fc10\x1e1 \x1fa고우영 지음\x1e00\x1fa(고우영 만화) 십팔사략\x1fn10 : 북송시대 남송시대\x1fd고우영 지음\x1e  \x1fa파주:\x1fb애니북스\x1fc2019\x1e  \x1fa255 p.:\x1fc23 cm\x1fe \x1e0 \x1fb\\10000\x1e\x1d'
sample = '00451namk   00157 k 4500005001500000008004100015020002600056049001800082056000800100090001700108100002700125245006500152260004300217300002200260950001100282\x1e20230604121247\x1e190115s2018    ulka          000a  kor  \x1e  \x1fa9788956057842\x1fc\\14500\x1e0 \x1flHK10005558\x1fc2\x1e  \x1fa843\x1e  \x1fa843\x1fb테ㄷ\x1fc \x1e1 \x1fa테드 창,옮긴이: 김상훈\x1e00\x1fa당신 인생의 이야기  : 테드 창 소설\x1fd테드 창,옮긴이: 김상훈\x1fn\x1e  \x1fa서울:\x1fb엘리 :북하우스 퍼블리셔스\x1fc2018\x1e  \x1fa447 p.:\x1fc21 cm\x1fe \x1e0 \x1fb\\14500\x1e\x1d'

if __name__  == "__main__":

    marc = MARC(sample, debug=True)
    marc.decode()
    #print(self.marc)
    print(f"Header: {marc.header}")
    #print(f"Direct: {directory}")
    #print(len(directory))
    #print(f"Data  : {data}")
    for entry in marc.groups:
        print(f"Group [{entry}]")
    print(len(marc.marc))
    marc.check()
    print(marc.encode())
    print(f"BOOK INFO: {marc.getBookInfo()}")
