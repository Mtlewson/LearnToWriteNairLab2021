#Engineers: Sean Duback, Robert Geoffrion
#School: Weber State University
#Project: Motion Tracking
#Year: 2019 Academic Year

#Engineers: Michael Lewson
#School: Chapman University
#Project: Motion Tracking
#Year: 2021 Academic Year

from os import listdir
from os.path import isfile, join
import numpy as np
import cv2
import math
#import paho.mqtt.client as mqtt
from PIL import Image, ImageDraw
import pandas as pd

import asyncio
import random
#import logging

import logging
import time

import msvcrt
from bleak import BleakClient

import copy
############################################################ Global Variables ###############################################

#excelFilePath = 'letter_images/Letter_L_Excelv2.xls' #grabs the decision windows from excel file
excelFilePath = 'letter_images/Letter_L_Excel.xlsx' #grabs the decision windows from excel file

df = pd.read_excel(excelFilePath, index_col=0) #grabs excel file converts to data file
letter = df.to_numpy() #converts to numpy


address = "7c:9e:bd:ee:7a:82"#'7c:9e:bd:ee:7a:80'#"3C:71:BF:FF:5E:5A" # Change the MAC address for your specific ESP32 here
UUID_NORDIC_TX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
UUID_NORDIC_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


#y: 0 is B2
#y -1 is the bottommost y point
#letter[y][x]
#x 0 is B
#x -1 is the furthest x point point

white = [255,255,255]
black = [0,0,0]
nearBlack = [5,5,5]
dWinList = []


pixDistance = 0
pixDistFirst = []
pixDirFirst = {}
pixDistSecond = []
pixDirSecond = {}
pixDistStart = 100
minPixDist = {}
# grab the reference to the webcam
camera = cv2.VideoCapture(0)
# define the lower and upper boundaries of the "orange"
colorLower = (0, 120, 70)
colorUpper = (50, 255, 180)
winNum = 0

startFlag = False
oldStartFlag = False
endFlag = False
score = 0



# Configure logging parameters
#log_date = time.strftime("%Y%m%d_%H%M%S", time.localtime())
log_date = time.strftime("%d-%m-%Y-%H_%M_%S", time.localtime())
log_name = "LTW2.3_log_" + log_date + ".log"
logging.basicConfig(filename="log_files/"+log_name, filemode="a", format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                    level=logging.DEBUG)


############################################################# Class Definitions #################################################

class Dwin(object):
    def __init__(self, idnum=0, ymin=0, ymax=0, xmin=0, xmax=0):
        self.idnum = idnum
        self.ymin = ymin
        self.ymax = ymax
        self.xmin = xmin
        self.xmax = xmax


############################################################# Functions ###########################################

def colorDwin (img, class_type="Dwin"):
    #func used for debugging colors in the dWins black and makes the letter white
    for Dwin in dWinList:
        print ("Window#= %s, xmin=%s, xmax= %s, ymin= %s ymax= %s"% (Dwin.idnum, Dwin.xmin, Dwin.xmax, Dwin.ymin, Dwin.ymax))
        for x in range(Dwin.xmin, Dwin.xmax):
            for y in range(Dwin.ymin, Dwin.ymax, -1):
                if np.array_equal(img[y, x], black):
                    #print ("x=%s y=%s"%(x, y))
                    img[y, x] = white
                else:
                     img[y, x] = 0

#function to show decision windows, avoid using with rest of program active
def showDwin():
    letter_image = extractImageFromExcel(letter)
    #extracts decision windows
    extractDecisionWindowsFromExcel()
    #colors the decision windows over the image
    colorDwin(letter_image)
    #shows the image
    letter_image = Image.fromarray(letter_image)
    letter_image.show()

def totalDistance(x0, y0, x1, y1):
    return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)


def start (img, inputX, inputY):

    for x in range(dWinList[0].xmin, dWinList[0].xmax):
        for y in range(dWinList[0].ymin, dWinList[0].ymax, -1):
            if np.array_equal(img[y, x], black):
                pixDistStart = int(totalDistance(x, y, inputX, inputY))
                if pixDistStart <= 5:
                    return True
    return False

def getdirection(inputX, inputY, x, y):
    yDistance = y - inputY
    xDistance = x - inputX
    if abs(yDistance) >= abs(xDistance):
        if y >inputY: return 3
        else: return 1
    else:
        if x > inputX: return 4
        else: return 2


def getMinDistance (img, dWinNum, inputX, inputY, score):
    FirstKey = 0 #used as flags for distance to not update min distince if no new values
    SecondKey = 0 #used as flags for distance to not update min distince if no new values
    direction = 0
    #print("DwinNum = %s"%(dWinNum))  #used for debugging
    dWinNumEnd = len(dWinList)-2
    # if dWinNum == 36: #if the game is over return end game true, no currect dWin 36 in logic, game will never end
    #     return 36, 0, True
    if dWinNum == dWinNumEnd: #if the game is over return end game true, no currect dWin 36 in logic, game will never end
        return dWinNumEnd, 0, True, 0, 0
    else:

        for x in range(dWinList[dWinNum].xmin, dWinList[dWinNum].xmax):
            for y in range(dWinList[dWinNum].ymin, dWinList[dWinNum].ymax, -1):
                if np.array_equal(img[y, x], black):
                    yDistance = y - inputY
                    xDistance = x - inputX
                     #numpy.allclose(a, b, rtol=0, atol=3, equal_nan=False)
                    if yDistance <= 2 and xDistance <= 2: # a two pixel tolerance is added to the first window as a handicap for the user
                        print("I am here A:")
                        print((inputX in range(dWinList[dWinNum].xmin, dWinList[dWinNum].xmax) and inputY in range(dWinList[dWinNum].ymax, dWinList[dWinNum].ymin)))
                        #print(dWinList[dWinNum].xmin, dWinList[dWinNum].xmax) and inputY in range(dWinList[dWinNum].ymax, dWinList[dWinNum].ymin))
                        score = score +1
                        pixDistFirst.clear()
                        pixDistSecond.clear()
                        pixDirFirst.clear()
                        pixDirSecond.clear()
                        #print("I am in early start-up")
                        return dWinNum, 0, False, score, direction
                    else:
                        FirstKey += 1 #Counts up as the loop goes on so every value has a unquie key in the dict
                        totalDisOne = int(totalDistance(x, y, inputX, inputY)) #the distance of the user input from the black pixel is calculated
                        pixDistFirst.insert(FirstKey, totalDisOne) #the distance is stored in a dict with the "FirstKey" acting as the key
                        pixDirFirst[totalDisOne] =  getdirection(inputX, inputY, x, y) #A direction is stored with using the distance as its location in a list


        for x in range(dWinList[dWinNum+1].xmin, dWinList[dWinNum+1].xmax):
            for y in range(dWinList[dWinNum+1].ymin, dWinList[dWinNum+1].ymax, -1):
                if  np.array_equal(img[y, x],black):
                    if np.array_equal(img[y,x], [inputY, inputX]): #if the input is on a letter pixel add one to score and return
                        print("I am here B:")
                        score = score +1
                        pixDistFirst.clear()
                        pixDistSecond.clear()
                        pixDirFirst.clear()
                        pixDirSecond.clear()
                        print("dw found for dwin #%s, x:%s, y:%s, "% (dWinNum+1, x, y))
                        return dWinNum+1, 0, False, score, direction
                    else:
                        SecondKey += 1 #Counts up as the loop goes on so every value has a unquie key in the dict
                        totalDisTwo = int(totalDistance(x, y, inputX, inputY))
                        pixDistSecond.insert(SecondKey, totalDisTwo)
                        pixDirSecond[totalDisTwo] =  getdirection(inputX, inputY, x, y)

        if FirstKey != 0:
            minPixDist.update({dWinNum: min(pixDistFirst)}) #the minimum distance from the first Dwin is taken
        else: minPixDist[dWinNum] = 1000 #used to asign a value to minPixDist if none was found
        if SecondKey != 0:
            minPixDist.update({dWinNum+1: min(pixDistSecond)})  #the minimum distance from the second Dwin is taken
        else: minPixDist[dWinNum+1] = 1000  #used to asign a value to minPixDist if none was found
        next_dwin = dWinList[dWinNum+1]
        print("window:", dWinNum+1, "x", inputX, next_dwin.xmin, next_dwin.xmax, "y", inputY, next_dwin.ymax, next_dwin.ymin)
        if (inputX in range(next_dwin.xmin-10, next_dwin.xmax+10) and inputY in range(next_dwin.ymax-10, next_dwin.ymin+10)): #compares the two min distances
            print("I am here C:")
            #if inputX in range(next_dwin.xmin, next_dwin.xmax) and inputY in range(next_dwin.ymin, next_dwin.ymax):
            direction = pixDirSecond[minPixDist[dWinNum+1]] #grabs the direction associated with the minimum distance
            #print ("Window#= %s, Distance = %s, direction = %s"% (dWinNum+1, minPixDist[dWinNum+1], direction))  #used for debugging
            print ("Window#= %s, Distance = %s, direction = %s"% (dWinNum+1, minPixDist[dWinNum+1], direction))  #used for debugging
            pixDistFirst.clear()
            pixDistSecond.clear()
            pixDirFirst.clear()
            pixDirSecond.clear()
            #print("dw found 2 for dwin #%s, x:%s, y:%s, "% (dWinNum+1, x, y))
            return dWinNum+1, minPixDist[dWinNum+1], False, score, direction
            # for x in range(dWinList[dWinNum].xmin, dWinList[dWinNum].xmax):
            #     for y in range(dWinList[dWinNum].ymin, dWinList[dWinNum].ymax, -1):
            # direction = pixDirSecond[minPixDist[dWinNum+1]] #grabs the direction associated with the minimum distance
            # #print ("Window#= %s, Distance = %s, direction = %s"% (dWinNum+1, minPixDist[dWinNum+1], direction))  #used for debugging
            #
            # print ("Window#= %s, Distance = %s, direction = %s"% (dWinNum+1, minPixDist[dWinNum+1], direction))  #used for debugging
            # pixDistFirst.clear()
            # pixDistSecond.clear()
            # pixDirFirst.clear()
            # pixDirSecond.clear()
            # #print("dw found 2 for dwin #%s, x:%s, y:%s, "% (dWinNum+1, x, y))
            # return dWinNum+1, minPixDist[dWinNum+1], False, score, direction
            #returns the new dWinNum, min distance, flag signaling the game is to continue, the current score, and direction
        #end the gmae here elif dwin 36 ... need to make it go to dwin 36 no current logic for a 36th decision window
# =============================================================================
#         else:
#             return dWinNum, 0, True, score, direction
# =============================================================================
        else:
            print("I am here D")
            print("Is valid input: ", (inputX in range(next_dwin.xmin-10, next_dwin.xmax+10) and inputY in range(next_dwin.ymax-10, next_dwin.ymin+10)))
            direction = pixDirFirst[minPixDist[dWinNum]]
            #print ("Window#= %s, Distance = %s, direction = %s"% (dWinNum, minPixDist[dWinNum], direction)) #used for debugging
            pixDistFirst.clear()
            pixDistSecond.clear()
            pixDirFirst.clear()
            pixDirSecond.clear()
            return dWinNum, minPixDist[dWinNum], False, score, direction



def extractEntireImage(address):
    print()

#function to grab the letter image from excel (but not the decision windows)
def extractImageFromExcel(letter):
    #grabs a numpy array of excel
    #letter_array = np.array(letter, dtype=np.uint8)
    letter_array = letter
    height = letter_array.shape[0]
    width = letter_array.shape[1]
    #height = 256
    #width = 256
    print("width, height", width,height)

    #creates a new array for the image (because can't change the type of numpy array to be proper pixels)
    rows, cols = (height, width)
    image_arr=[]
    for i in range(rows):
        col = []
        for j in range(cols):
            col.append((255,255,255))
        image_arr.append(col)

    for yRow in range(0, height):
      for xColumn in range(0, width):
          if (not math.isnan (letter_array[yRow][xColumn])) and (letter_array[yRow][xColumn] == 0): #black pixels
              image_arr[yRow][xColumn] = (0, 0, 0)
          #else:
            #  image_arr[yRow][xColumn] = (0, 0, 0)

    image_array_numpy = np.array(image_arr, dtype=np.uint8)

    # new_image_temp = Image.fromarray(image_array_numpy)
    # new_image_temp.show()

    return image_array_numpy

def readDirectoriesForFiles():
    mypath = "letter_images"
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    option_list = []
    file_dict = {}


    for i in range (0, len(onlyfiles)):
        file_dict[str(i)]=onlyfiles[i]
        filename = onlyfiles[i].replace("_Excel", "").replace(".xlsx", "").replace(".xls","").replace("_", " ")
        #filename.replace(".png", "").replace(".jpeg", "")
        print("option:", i, filename)
        #option_list.append(str(i))

    valid_input = False
    filename = ""
    while valid_input == False:
        user_input = input("Please enter number of file to select\n")
        if user_input in file_dict.keys():
            valid_input = True
            print(file_dict[user_input], "selected!")
            excelFilePath = 'letter_images/' + file_dict[user_input]
            df = pd.read_excel(excelFilePath, index_col=0) #grabs excel file converts to data file
            letter = df.to_numpy()
            return letter
        elif user_input.lower() == "quit":
            print("quitting")
            return letter
            break
        else:
            print("invalid input, please enter 0, 1, 2 etc, or quit ")


#function to grab the decision windows from excel
def extractDecisionWindowsFromExcel():
    dwDict = {}

    height = letter.shape[0]
    width = letter.shape[1]
    #extracts the coordinates of the decision windows by reading through excel file
    for yRow in range(0, height):
      for xColumn in range(0, width):
          #if letter[yRow][xColumn]!= 'nan':
          if not (math.isnan (letter[yRow][xColumn])):
              DW_Number = letter[yRow][xColumn]
              if DW_Number in dwDict:
                  #to be replaced with coordinates
                  dwDict[DW_Number] += [xColumn, yRow]
              else:
                  #first value of it found, creates the section
                  dwDict[DW_Number] = [xColumn, yRow]

    print("number of decision windows", len(dwDict))
    #print(dwDict)
     #dw format: Ymin, YMax, XMin, XMax
    for key in dwDict:
        if len(dwDict[key]) == 4:
            #print(dwDict[key])
            x1 = dwDict[key][0]
            x2 = dwDict[key][2]
            y1 = dwDict[key][1]
            y2 = dwDict[key][3]
            #print(dwDict[key][1], dwDict[key][3])
            #print(y1,y2,x1,x2)

            #determine Ymin, YMax, XMin, XMax
            #ymin is bigger
            #xmax is bigger
            if y1 > y2:
                yMin = y1
                yMax = y2
            else:
                yMin = y2
                yMax = y1
            if x1 > x2:
                xMax = x1
                xMin = x2
            else:
                xMax = x2
                xMin = x1
            #Ymin, YMax, XMin, XMax

            dWinList.append(Dwin(key, yMin, yMax, xMin, xMax))


        #else:
        #    print("Please ensure there are 2 points per decision window")
            #print(dwDict[key])
        dWinList.sort(key=lambda x: x.idnum, reverse=False)
        #ut.sort(key=lambda x: x.count, reverse=True)

def init():

    #so we have an excel file of the image with numbers marked for each coord
    #find the coord of each number then make the decision window from there

    height = letter.shape[0]
    width = letter.shape[1]
    #grabs the image
    # letter_image = extractImageFromExcel(letter)
    # #extracts decision windows
    extractDecisionWindowsFromExcel()




async def main(address, loop, letter_input):
    startFlag = False
    oldStartFlag = False
    endFlag = False
    score = 0
    letter = copy.deepcopy(letter_input)
    prevDwinNumber = 0

    refresh_counter = 0


    winNum = 0
    while True:  # Loop to allow reconnection
        try: # Attempt to connect to ESP32
            print("Connecting\n")
            async with BleakClient(address, loop=loop) as client:
                print("Connected!\n")
                while True: # Main loop, user selects test case
                    #EDIT here
                    #EDIT HERE
                    #letter = extractImageFromExcel(letter)
                    #extracts decision windows
                    #extractDecisionWindowsFromExcel()



                    cv2.imshow("Learn to Write!", letter)
                    key = cv2.waitKey(1) & 0xFF

                    # grab the current frame
                    (grabbed, frame) = camera.read()
                    frame = cv2.flip(frame, 1)

                    # resize the frame, blur it, and convert it to the HSV color space
                    blurred = cv2.GaussianBlur(frame, (11, 11), 0)
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                    # construct a mask for the color then perform a series of dilations and erosions to remove any small blobs left in the mask
                    mask = cv2.inRange(hsv, colorLower, colorUpper)
                    mask = cv2.erode(mask, None, iterations=2)
                    mask = cv2.dilate(mask, None, iterations=2)

                    # find contours in the mask and initialize the current (x, y) center of the ball
                    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
                    #center = None #why is center none?

                    # only proceed if at least one contour was found
                    if len(cnts) > 0:

                        # refresh_counter +=1
                        # if refresh_counter >= 100:
                        #     refresh_counter = 0
                        #     print("refresh")
                        #     letter = copy.deepcopy(letter_input)
                        #     prevDwinNumber = 0


                        # find the largest contour in the mask, then use centroid
                        c = max(cnts, key=cv2.contourArea)
                        ((x, y), radius) = cv2.minEnclosingCircle(c)
                        M = cv2.moments(c)
                        centerX = (int(M["m10"] / M["m00"])+50)
                        centerY = (int(M["m01"] / M["m00"])+50)
                        #print("X is %s, Y is %s"%(int(centerX),int(centerY))) #used for debugging
                        #if centerX < 800 and centerY < 600:
                        if startFlag == False: #Wait until input is near Dwin 0 to start game
                            cv2.circle(letter, (centerX, centerY), 1, (0, 0, 255), -1)
                            startFlag = start(letter, centerX,centerY)
                        else:
                            if oldStartFlag == False: #Clean the img on game start
                                oldStartFlag = True
                                #letter = cv2.imread('bw_image.png', 1)
                                letter = copy.deepcopy(letter_input)

                                winNum, pixDistance, endFlag, score, direction = getMinDistance(letter, winNum, centerX, centerY, score)
                                cv2.circle(letter, (centerX, centerY), 1, (0, 0, 255), -1)
                            else: #Play the game
                                winNum, pixDistance, endFlag, score, direction = getMinDistance(letter, winNum, centerX, centerY, score)
                                #print(winNum)


                                current_Dwin = dWinList[winNum]
                                next_dwin = current_Dwin
                                if current_Dwin != len(dWinList):
                                  next_dwin = dWinList[winNum+1]
                                if prevDwinNumber != current_Dwin:
                                    prevDwinNumber = current_Dwin
                                    for x in range(current_Dwin.xmin, current_Dwin.xmax):
                                        for y in range(current_Dwin.ymin, current_Dwin.ymax, -1):
                                            if np.array_equal(letter[y, x], black):
                                                #print ("x=%s y=%s"%(x, y))
                                                continue

                                            else:
                                                letter[y, x] = (250, 80, 80)
                                    for x in range(next_dwin.xmin, next_dwin.xmax):
                                        for y in range(next_dwin.ymin, next_dwin.ymax, -1):
                                            if np.array_equal(letter[y, x], black):
                                                #print ("x=%s y=%s"%(x, y))
                                                continue
                                            else:
                                                letter[y, x] = (200, 200, 50)


                                cv2.circle(letter, (centerX, centerY), 1, (0, 0, 255), -1)
                                print ("Distance = %s, direction = %s, Win# %s"% (pixDistance, direction, winNum))
                                # print("Decision Window: xRange = %s, %s,  yRange = %s, %s"% (current_Dwin.xmin, current_Dwin.xmax, current_Dwin.ymin, current_Dwin.ymax))
                                # print("Next Decision Window: xRange = %s, %s,  yRange = %s, %s"% (next_dwin.xmin, next_dwin.xmax, next_dwin.ymin, next_dwin.ymax))
                                print(("center_x = %s, center_y = %s, Radius = %s"% (centerX, centerY, radius)))
                                # log_x = str(round(x, 2))
                                # log_y = str(round(y, 2))
                                # log_radius = log_x = str(round(radius, 2))
                                logging.info("x = %s, y = %s, Radius = %s"% (centerX, centerY, radius))
                                logging.info(("Decision Window: xRange = %s, %s,  yRange = %s, %s"% (current_Dwin.xmin, current_Dwin.xmax, current_Dwin.ymin, current_Dwin.ymax)))
                                logging.info("Next Decision Window: xRange = %s, %s,  yRange = %s, %s"% (next_dwin.xmin, next_dwin.xmax, next_dwin.ymin, next_dwin.ymax))
                                logging.info("Distance = %s, direction = %s, Win# %s"% (pixDistance, direction, winNum))
                                # msg = ("{0},{1}".format(direction, pixDistance))
                                # print(msg)

                                #user_command = b"1," + b"2,"
                                # user_command = b"1,2"
                                # intensity = b'2'
                                #print(bytearray(b"3,1"))
                                user_command = b"1,2"
                                #intensity =  b'2'

                                if pixDistance < 50:
                                    intensity =  b'0'
                                elif pixDistance < 100:
                                    intensity = b'1'
                                elif pixDistance < 200:
                                    intensity = b'2'
                                elif pixDistance < 500:
                                    intensity = b'3'
                                else:
                                    intensity =  b'0'

                                # print("going to transmit here!")
                                #thing = ("{0},{1}".format(direction, 2))
                                if direction == 1: #forward
                                    user_command = b"1," + intensity
                                elif direction ==2: #left
                                    user_command = b"2," + intensity

                                elif direction == 3: #back
                                    user_command = b"3," + intensity

                                elif direction == 4: #right
                                    user_command = b"4," + intensity


                                #command_list = [b"1,2", b"2,2", b"3,2", b"4,2"]
                                # print(bytearray(user_command[0:20]))
                                await client.write_gatt_char(UUID_NORDIC_TX, bytearray(user_command[0:20]), True)
                                # print("transmitted")



                    cv2.imshow("Learn to Write!", letter)
                    key = cv2.waitKey(1) & 0xFF

                    # if the q key is pressed, stop the loop
                    if key == ord("q") or endFlag == True:
                        #msg = ("{0},{1}".format(0, 0 ))
                        #client.publish("motors",msg)
                        print("Your Score is %s letter pixels hit out of 611 letter pixels"%(score))
                        break

                break
        except Exception as e: # Catch connection exceptions, usually "device not found," then try to reconnect
            print(e)
            print('Trying to reconnect...')
            continue

############################################################# Main ########################################################
#extracts decision windows from excel
logging.info("\n\n")
logging.info("PROGRAM BEGINS")


letter = readDirectoriesForFiles()
init()
#gets letter from excel
letter = extractImageFromExcel(letter)
loop = asyncio.get_event_loop()
loop.run_until_complete(main(address, loop, letter))
camera.release()
cv2.destroyAllWindows()



###################################################################### ARCHIVE ###################################################################
#Below is a failed attempt at automating the creation of Decision Windows

# def isPixUp(img, y, x, wId):
#     y = y-3
#     for xw in range(x, x+2):
#         for yw in range(y-2, y):
#             if xw >= 1920: break
#             elif img[yw, xw] == 0:
#                 wId += 1
#                 dWinList.append(Dwin(wId, y, y-3, x, x+3, 'u'))
#                 return y, x, wId
#     return y, x, wId

# def isPixUpperRight(img, y, x, wId):
#     y = y-3
#     x = x+3
#     for xw in range(x, x+2):
#         for yw in range(y-2, y):
#             if xw >= 1920: break
#             elif img[yw, xw] == 0:
#                 wId += 1
#                 dWinList.append(Dwin(wId, y, y-3, x, x+3, 'ur'))
#                 return y, x, wId
#     return 0

# def isPixRight(img, y, x, wId):
#     x = x+5
#     for xw in range(x, x+4):
#         for yw in range(y-4, y+1):
#             if img[yw, xw] == 0:
#                 wId += 1
#                 dWinList.append(Dwin(wId, y, y-5, x, x+5, 'r'))
#                 return y, x, wId
#     return 0

# def isPixLeft(img, y, x, wId):
#     x = x - 10
#     for xw in range(x, x+4):
#         for yw in range(y-4, y):
#             if img[yw, xw] == 0:
#                 wId += 1
#                 dWinList.append(Dwin(wId, y, y-5, x, x+5, 'l'))
#                 return y, x, wId
#     return 0

# def isPixUpperLeft(img, y, x, wId):
#     y = y-5
#     x = x-5
#     for xw in range(x, x+4):
#         for yw in range(y-4, y):
#             if xw >= 1920: break
#             elif img[yw, xw] == 0:
#                 wId += 1
#                 dWinList.append(Dwin(wId, y, y-5, x, x+5, 'ul'))
#                 return y, x, wId
#     return 0

# def isPixDown(img, y, x, wId):
#     y = y+5
#     for xw in range(x, x+4):
#         for yw in range(y-4, y):
#             if xw >= 1920: break
#             elif img[yw, xw] == 0:
#                 wId += 1
#                 dWinList.append(Dwin(wId, y, y-5, x, x+5, 'd'))
#                 return y, x, wId
#     return

# def isPixDownLeft(img, y, x, wId):
#     y = y+5
#     x = x-5
#     for xw in range(x, x+9):
#         for yw in range(y-9, y):
#             if xw >= 1920: break
#             elif img[yw, xw] == 0:
#                 wId += 1
#                 dWinList.append(Dwin(wId, y, y-5, x, x+5, 'dl'))
#                 return y, x, wId
#     return 0

# def isPixDownRight(img, y, x, wId):
#     y = y+5
#     x = x+5
#     for xw in range(x, x+9):
#         for yw in range(y-9, y):
#             if xw >= 1920: break
#             elif img[yw, xw] == 0:
#                 wId += 1
#                 dWinList.append(Dwin(wId, y, y-5, x, x+5, 'dr'))
#                 return y, x, wId
#     return 0

# def createFirstDWindow(img, y, x, wId):
#     dWinList.append(Dwin(wId, y, y-5, x, x+5, 'fr')) #create first window at the most lower left pixel
#     return y, x, wId

# def initLetter(img, class_type = "Dwin"):
#     """Convert img to BW and Create Decision windows"""
#     #change the image to black and white
#     changeToBW(img)
#     # find the height, width, of the image
#     ys = img.shape[0]
#     xs = img.shape[1]
#     oneTimeFlag = 1
#     wId = 1
#     #iterate over image starting at bottom left to find most lower left pixel
#     x = 0
#     y = ys-1
#     while x < xs-1:
#         y = ys-1
#         while  y > 0:
#             if img[y, x] == 0:
#                 if oneTimeFlag:
#                     oneTimeFlag = 0
#                     y, x, wId = createFirstDWindow(img, y, x, wId)
#                     y, x, wId = isPixUp(img, y, x, wId)
#                     y, x, wId = isPixUpperRight(img, y, x, wId)
#                     y, x, wId = isPixUp(img, y, x, wId)
#                     y, x, wId = isPixUpperRight(img, y, x, wId)


#                     return
#             else:
#                 y -= 1
#         x += 1
