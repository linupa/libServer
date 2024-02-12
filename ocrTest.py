import cv2
import pytesseract
import numpy as np
import imutils
import math

global gVerbose
gVerbase = False
WIDTH = 600
HEIGHT = 800

def Print(arg):
    if gVerbose:
        print(arg)

def grCmp(g):
    return g[0]

def filterOutliers(lines):
    upperBound = HEIGHT / 2 + 80
    lowerBound = HEIGHT / 2 - 80
    ret = list()
    for line in lines:
        points = line[0]
        x1,y1,x2,y2=points

        if y1 > upperBound or y1 < lowerBound or y2 > upperBound or y2 < lowerBound:
            continue

        ret.append(points)

    return ret


def getBarcode(lines):
    THRESHOLD = 5
    hl = dict()
    vl = list()
    for i in range(len(lines)):
        points = lines[i]
        x1, y1, x2, y2 = points
        v = np.array([x2-x1, y2-y1])
        th = math.atan2(y2-y1, x2-x1)
        Print(f"{points} : {th}")
        if abs(th) < math.pi * 5 / 180.:
            hl[i] = (y1+y2) / 2
        elif abs(th) > math.pi * 85 / 180.:
            vl.append(points)
    Print(hl)
    if len(hl) == 0:
        return list()

    grs = list()
    for i in hl:
        h = hl[i]
        for gr in grs:
            if abs(h - gr[0]) < THRESHOLD:
                gr[1].append(i)
                s = 0
                for j in gr[1]:
                    s += hl[j]
                gr[0] = s / len(gr[1])
                break;
        else:
            grs.append([hl[i], [i]])
    Print(grs)

    for gr in grs:
        l = lines[gr[1][0]][0]
        r = lines[gr[1][0]][0]
        ly = lines[gr[1][0]][1]
        ry = lines[gr[1][0]][1]
        for i in gr[1]:
            x1 = lines[i][0]
            y1 = lines[i][1]
            x2 = lines[i][2]
            y2 = lines[i][3]
            if l > x1:
                l = x1
                ly = y1
            if l > x2:
                l = x2
                ly = y2
            if r < x1:
                r = x1
                ry = y1
            if r < x2:
                r = x2
                ry = y2
        gr[0] = math.sqrt((l-r)**2 + (ly-ry)**2)
        gr[1] = [l, ly, r, ry]
    grs.sort(reverse=True, key=grCmp)

    Print("barcodes")
    Print(grs)
    if len(grs) < 2:
        return list()
    return [grs[0][1], grs[1][1]] + vl

def clearOutside(closed, hl):
    if hl[0][1] > hl[1][1]:
        upper = hl[1]
        lower = hl[0]
    else:
        upper = hl[0]
        lower = hl[1]
    cv2.rectangle(closed, (0, 0), (WIDTH, upper[1]), (0,0,0), -1)
    cv2.rectangle(closed, (0, HEIGHT), (WIDTH, lower[3]), (0,0,0), -1)

    return closed

def rotate_image(image, image_center, angle):
    Print(image.shape)
    Print(type(image_center))
    Print(image_center)
#    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    Print(type(image_center))
    Print(image_center)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
    return result

def getBoundary(box):
    minY = minX = 9999
    maxY = maxX = 0
    for p in box:
        if p[0] > maxY:
            maxY = p[0]
        elif p[0] < minY:
            minY = p[0]
        if p[1] > maxX:
            maxX = p[1]
        elif p[1] < minX:
            minX = p[1]
    v1 = box[0] - box[1]
    v2 = box[1] - box[2]
    l1 = np.linalg.norm(v1)
    l2 = np.linalg.norm(v2)
    Print(v1)
    Print(v2)
    Print(l1)
    Print(l2)

    lower = set()
    if l2 > l1:
        if v1[1] > 0:
           lower.add(0)
           lower.add(3)
        else:
           lower.add(1)
           lower.add(2)
        ver = v1
        hor = v2
        width = l2
        height = l1
    else:
        if v2[1] > 0:
            lower.add(1)
            lower.add(0)
        else:
            lower.add(2)
            lower.add(3)
        ver = v2
        hor = v1
        width = l1
        height = l2

    if np.dot(ver, (0,1)) < 0:
        ver = ver * -1
    if np.dot(hor, (1,0)) < 0:
        hor = hor * -1

    return [hor, ver, width, height, lower]



#f = 'image_67192321.JPG'
#f = 'image_67202561.JPG'
#f = 'image_67163137.JPG'
#f = 'image.png'

def getStd(line):
    s = 0.0
    ss = 0.0
    l = len(line)
    for p in line:
        b = float(p)
        s += b
        ss += b * b
    mean = s / l
    return ss / l - mean * mean

class OCRTest:
    def readText(self, filename, verbose=False):
        global gVerbose
        gVerbose = verbose

        self.img = cv2.imread(filename)
        print(self.img.shape)

#        self.img2 = cv2.resize(self.img, (WIDTH, HEIGHT))
        self.img2 = self.img[1500:2500, 0:3024]
#        self.img2 = self.img

        gray = cv2.cvtColor(self.img2, cv2.COLOR_BGR2GRAY)


        vhf = np.array([[0.0, 0.0, 0.0], [-1.0, 0.0, 1.0], [0.0, 0.0, 0.0]])

        #imghf = cv2.filter2D(gray, -1, vhf)

        ddepth = cv2.cv.CV_32F if imutils.is_cv2() else cv2.CV_32F
        gradX = cv2.Sobel(gray, ddepth=ddepth, dx=1, dy=0, ksize=-1)
        gradY = cv2.Sobel(gray, ddepth=ddepth, dx=0, dy=1, ksize=-1)
        self.gradX = 0
        self.gradY = 0

        grad = cv2.subtract(gradX, gradY)
        grad = cv2.convertScaleAbs(grad)

        blurred = cv2.blur(grad, (11,11))
        (_, thresh) = cv2.threshold(blurred, 150, 255, cv2.THRESH_BINARY)

        kernel = np.ones((5,5), np.uint8)
        #thresh = cv2.erode(thresh, kernel)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        closed = cv2.erode(closed, None, iterations = 4)
        closed = cv2.dilate(closed, None, iterations = 4)

        edges = cv2.Canny(closed, 50, 150, apertureSize=3)

        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=5, maxLineGap=20)
        Print("Lines")
        Print(lines)
        lines = filterOutliers(lines)
        hl = getBarcode(lines)
        Print(hl)

#        closed = clearOutside(closed, hl)

        cnts = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        if len(cnts) == 0:
            return ""
        c = sorted(cnts, key = cv2.contourArea, reverse = True)[0]

        #epsilon = 0.02*cv2.arcLength(c,True)
        #c = cv2.approxPolyDP(c,epsilon,True)

        Print("c")
        Print(c)
        rect = cv2.minAreaRect(c)
        #rect = cv2.boundingRect(c)
        #closed = cv2.fillPoly(closed, rect, [128,128,128])
        Print("rect")
        Print(rect)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        Print(box)
        hor, ver, width, height, lower = getBoundary(box)

        Print(f'Vert {ver}')
        Print(f'Hor  {hor}')
        #angle =  math.acos(np.dot(hor, (1,0) / np.linalg.norm(hor)))
        angle =  math.atan2(hor[1], hor[0])
        Print(f'Angle {angle*180/math.pi}')

        barcodeBox = box.copy()
        Print(f'box {barcodeBox}')

        lowerLeft = None
        for i in lower:
            Print(f'{i} {lowerLeft}')
            if lowerLeft == None or barcodeBox[lowerLeft][0] > barcodeBox[i][0]:
                lowerLeft = i
        Print(f'lowerLeft {lowerLeft}')

        rotated = rotate_image(self.img2, tuple([float(barcodeBox[lowerLeft][0]), float(barcodeBox[lowerLeft][1])]), angle*180/math.pi)
#        rotated = self.img2

        textBox = barcodeBox.copy()
        for i in range(4):
            if i in lower:
                textBox[i] = barcodeBox[i] + ver * 0.6
            else:
                textBox[i] = barcodeBox[i] + ver + np.array([0, 5])

        #img3 = self.img2[textBox[0][1]:textBox[2][1], textBox[0][0]:textBox[1][0]]
        Print(f'{width} x {height}')
        if width < 10 or height < 5:
            return ""

        rotatedGray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        rotatedGray = cv2.filter2D(rotatedGray, -1, kernel)

        lf = np.array(barcodeBox[lowerLeft])
        print(f"LF {lf}")
        detections = set()
        trials = 0
        left = lf[0]
        right = lf[0] + int(width)
        if right >= WIDTH:
            right = WIDTH
        '''
        # Check area above the line
        stddevs = dict()
        maxStd = None
        minStd = None
        for i in range(5, 40):
            line = rotatedGray[lf[1] - i, left:right]
            stddev = getStd(line)
            stddevs[i] = stddev
            if not minStd or minStd > stddev:
                minStd = stddev
                minIdx = i

        for i in range(5, minIdx+1):
            line = rotatedGray[lf[1] - i, left:right]
            stddev = getStd(line)
            stddevs[i] = stddev
            if not maxStd or maxStd < stddev:
                maxStd = stddev

        print(stddevs)
        upper = maxStd * 0.8
        lower = minStd * 5
        print(f"Min/Max {minStd} {maxStd}")
        print(f"Lower/Upper {lower} {upper}")

        check = False
        for i in range(5, 40):
            stddev = stddevs[i]
            if stddev > upper:
                check = True
#            if stddev > lower or not check:
#                continue
            img3 = rotatedGray[lf[1]-i:lf[1]+10, left:right]
            text = pytesseract.image_to_string(img3)
            trials += 1
            texts  = text.split("\n")
            for text in texts:
                text = text.replace(" ", "").replace("-", "").replace("_","").replace(".","")
                if len(text) > 0 and len(text) < 20:
                    detections.add(text)

        # Check area below the line
        stddevs = dict()
        maxStd = None
        minStd = None
        for i in range(5, 60):
            line = rotatedGray[lf[1] + i, left:right]
            stddev = getStd(line)
            stddevs[i] = stddev
            if not minStd or minStd > stddev:
                minStd = stddev
                minIdx = i

        for i in range(5, minIdx+1):
            line = rotatedGray[lf[1] - i, left:right]
            stddev = getStd(line)
            stddevs[i] = stddev
            if not maxStd or maxStd < stddev:
                maxStd = stddev
        print(stddevs)
        upper = maxStd * 0.8
        lower = minStd * 5.0
        print(f"Min/Max {minStd} {maxStd}")
        print(f"Lower/Upper {lower} {upper}")

        check = False
        for i in range(5, 60):
            stddev = stddevs[i]
            if stddev > 1000:
                check = True
            if stddev > 500 or not check:
                continue
            img3 = rotatedGray[lf[1]-10:lf[1]+i, left:right]
            text = pytesseract.image_to_string(img3)
            trials += 1
            texts  = text.split("\n")
            for text in texts:
                text = text.replace(" ", "").replace("-", "").replace("_","").replace(".","")
                if len(text) > 0 and len(text) < 20:
                    detections.add(text)

        print(detections)
        print(trials)
        '''

        txtBox = np.array([
            lf,
            lf + np.array([int(width), 0]),
        ])


        RATIO = 0.3
        s = 0.0
        count = 0
        height = 40
        '''
        for i in range(60, 5, -1):
            line = rotatedGray[lf[1] + i, left:right]
            stddev = getStd(line)
            if count and s * RATIO / count > stddev:
                height = i
                break;
            s += stddev
            count += 1
        '''
#        lf[1] += 10
        print(f"Height {height}")
        img3 = rotatedGray[lf[1]-int(height):lf[1]+10 , left:right]

        '''
        text = pytesseract.image_to_string(img3)
        print(text)
        texts  = text.split("\n")
        for text in texts:
            text = text.replace(" ", "").replace("-", "").replace("_","").replace(".","")
            if len(text) > 0 and len(text) < 20:
                detections.add(text)

        height = 80
        img3 = rotatedGray[lf[1]-int(height):lf[1]+10 , left:right]
        text = pytesseract.image_to_string(img3)
        texts  = text.split("\n")
        for text in texts:
            text = text.replace(" ", "").replace("-", "").replace("_","").replace(".","")
            if len(text) > 0 and len(text) < 20:
                detections.add(text)

        img3 = rotatedGray[lf[1]-10:lf[1]+int(height), left:right]
        text = pytesseract.image_to_string(img3)
        texts  = text.split("\n")
        for text in texts:
            text = text.replace(" ", "").replace("-", "").replace("_","").replace(".","")
            if len(text) > 0 and len(text) < 20:
                detections.add(text)
        '''

        Print(f'text [{detections}]')
        self.gradX = gradX
        self.gradY = gradY
        self.blurred = blurred
        self.thresh = thresh
        self.grad = grad
        self.closed = closed
        self.box = box
        self.img3 = img3
        self.txtBox = txtBox
        self.textBox = textBox
        self.rotated = rotated
        self.c = c
        self.hl = hl
        self.lines = lines

        return detections

    def display(self):
        gradX = self.gradX
        gradY = self.gradY
        blurred = self.blurred
        thresh = self.thresh
        grad = self.grad
        closed = self.closed
        box = self.box
        img2 = self.img2
        img3 = self.img3
        txtBox = self.txtBox
        textBox = self.textBox
        rotated = self.rotated
        c = self.c
        hl = self.hl
        lines = self.lines

        cv2.imshow('original', self.img)
        cv2.imshow('resize', self.img2)
        cv2.imshow('gradX', gradX)
        cv2.imshow('gradY', gradY)
        cv2.imshow('blurred', blurred)
        cv2.imshow('thresh', thresh)
        cv2.imshow('grad', grad)
        cv2.drawContours(closed, [box], -1, (0, 255, 0), 1)
        cv2.imshow('closed', closed)
#        cv2.imshow('cropped', img3)
        Print(txtBox)
        Print(type(txtBox))
#        cv2.drawContours(rotated, [box], -1, (255, 0, 0), 1)
        cv2.drawContours(rotated, [txtBox], -1, (0, 0, 255), 1)
        cv2.imshow('rotated', rotated)
        #cv2.imshow('HF', imghf)
        #cv2.imshow('img', img3)
        upper = int((HEIGHT / 2) + 80)
        lower = int((HEIGHT / 2) - 80)

        Print(textBox)
        Print(type(textBox))
        cv2.drawContours(img2, [c], -1, (255, 0, 255), 1)
#        for points in lines:
#            x1,y1,x2,y2=points
#            cv2.line(img2,(x1,y1),(x2,y2),(255,0,255),1)

#        for points in hl:
#            # Extracted points nested in the list
#            Print(points)
#            x1,y1,x2,y2=points
#            Print(points)
#            # Draw the lines joing the points
#            # On the original image
#            cv2.line(img2,(x1,y1),(x2,y2),(255,255,0),1)
#            # Maintain a simples lookup list for points
        #    lines_list.append([(x1,y1),(x2,y2)])
        #cv2.drawContours(img2, [box], -1, (0, 255, 0), 1)
        #cv2.drawContours(img2, [textBox], -1, (0, 0, 255), 3)
#        cv2.line(img2, (1, upper), (WIDTH, upper), (0, 0, 255), 1)
#        cv2.line(img2, (1, lower), (WIDTH, lower), (0, 0, 255), 1)
        cv2.drawContours(img2, [box], -1, (255, 0, 0), 1)
        cv2.imshow('gray', img2)

        #cv2.minMaxLoc(img3)

        cv2.waitKey(0)

        cv2.destroyAllWindows()

if __name__ == '__main__':
    ocrTest = OCRTest()
    ret = ocrTest.readText('image.jpg', True)
#    if len(ret) > 0:
    ocrTest.display()


