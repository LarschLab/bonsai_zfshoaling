import clr
from System import Array
clr.AddReference("OpenCV.Net")
from OpenCV.Net import Mat, CV, Depth
import math

def transf(x,y,hArr):

  h = Mat.FromArray(hArr, 3, 3, Depth.F64, 1)

  values1 = Array[float]([x,y])
  values2 = Array[float]([1,1])

  point = Mat.FromArray(values1, 1, 1, Depth.F64,2)
  out = Mat.FromArray(values2, 1, 1, Depth.F64,2)

  CV.PerspectiveTransform(point,out,h)

  x=out.Item[0].Val0
  y=out.Item[0].Val1

  return x,y

def toGL(c,cMax):
  return int(2*(c-cMax/2))/cMax