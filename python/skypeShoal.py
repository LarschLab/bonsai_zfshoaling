import sys
import clr
clr.AddReference("OpenTK")
from OpenTK import Vector3
from System import Array, Tuple
import math

sys.path.append('C:\\Users\\jlarsch\\Documents\\bonsai_zfshoaling\\python')
import CameraInterceptCorrection as cic
#import geometry as geo


#Item1: (zip)
#  Item1: contour
#  Item2: ROI
#  Item3: animal pair matrix
#  Item4: projector-camera calibration matrix
#  Item5: videoSize
#  Item6: camHeight
#Item2: (Trajectory File)

def getAnimalCoors(value,allCoor):

    allwells=[]
    oldCoor=allCoor
    allCoor=[]
    i=0
    xMax = float(value.Item1.Item5.Width)
    yMax = float(value.Item1.Item5.Height)
    camHeight=float(value.Item1.Item6)
    #print(xMax,yMax)
    for w in range(len(value.Item1.Item1)):

        well=value.Item1.Item1[w]
        xoff=value.Item1.Item2[i].Item1
        yoff=value.Item1.Item2[i].Item2

        #Also correct dish ROI! Added 7-19-2017
        xoff,yoff = cic.CorrectFish(xoff,yoff,0,0,xMax,yMax,camHeight)

        x = well.Centroid.X
        y = well.Centroid.Y
        o=well.Orientation

        #use previous coordinates if current coordinates are NaN
        if math.isnan(x):
            if len(oldCoor)>0:
                x=oldCoor[w][0]
                y=oldCoor[w][1]
                xoff=oldCoor[w][2]
                yoff=oldCoor[w][3]
                o=oldCoor[w][4]
        else:
            x,y = cic.CorrectFish(x,y,xoff,yoff,xMax,yMax,camHeight)



        i+=1

        welldata = ((round(x)), (round(y)), o)
        allCoor.append([x,y,xoff,yoff,o])
        wellstr = "%0.f %0.f %0.3f" % welldata
        allwells.append(wellstr)
    #print(len(allCoor))


    # add one more row, representing pre recorded trajectory, episode name and disc size for visual stimulation
    xp = value.Item2.Item2
    yp = value.Item2.Item3
    sp = value.Item2.Item4  # sprite point size

    eName = value.Item2.Item1
    welldata = ((round(xp)), (round(yp)), sp, eName)
    allCoor.append([xp, yp, 0, 0, sp])
    wellstr = "%0.f %0.f %0.f %s" % welldata
    allwells.append(wellstr)
    return allCoor, allwells

def CLstim(value,allCoor,posList,p,ii,CLmode):
    o = posList[ii][4]  # current animal orientation
    xo = posList[ii][0] # current animal position
    yo = posList[ii][1]

    dx = p[0]   # stim position (animal centric)
    dy = p[1]

    dist = math.sqrt((dx ** 2) + (dy ** 2))
    if dist == 0:
        dist = 1

    phi = math.asin(dx / dist)

    heading = -o + (math.pi * (1 / 2.))
    # heading=o+(math.pi*(1/2))

    x = math.sin(heading + phi) * dist
    y = math.cos(heading + phi) * dist
    # print 'x',x,'y',y,'dist',dist,'phi',phi,'o',o,'heading',heading
    x = x + xo
    y = y + yo

    wellDiam = value.Item1.Item2[ii].Item3
    # print x,y,wellDiam
    # Remove stimuli that would extend into neighbor arena.
    if (x < wellDiam) and (x > 0) and (y < wellDiam) and (y > 0):
        x = x + allCoor[ii][2]
        y = y + allCoor[ii][3]
    else:
        # print 'not drawing dot for animal',ii
        x = 0
        y = 0

    return x,y

def getPairList(value, FlexPair):
    if FlexPair:
        eName = value.Item2.Item1
        pairListNr = int(eName[:2])
        numAn = len(value.Item1.Item3[0])
        return value.Item1.Item3[pairListNr * numAn:(pairListNr + 1) * numAn]
    else:
        return value.Item1.Item3  # animal pair matrix

def listToTkArray(list):
    return Array[Vector3]([Vector3(x[0], x[1], x[2]) for x in list])