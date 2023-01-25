import math

def runAvgList(oldList,newList,weight,threshold=0):

    if ((len(oldList)>0) & (~math.isnan(newList[0]))):

      newAll=[]
      for i,a in enumerate(newList):
        if abs(a-oldList[i])<threshold:
          newAll.append((float(weight)*oldList[i] + a)/float(weight+1))
        else:
          newAll.append(a)
      newList=newAll
      oldList=newList
      
    else:
      oldList=[float(0) for i in range(len(newList))]
      
    return newList,oldList