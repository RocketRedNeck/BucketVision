#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bucketvision

Many hands make light work!
A multi-threaded vision pipeline example for Bit Buckets Robotics that
looks like a bucket brigade

Makes use of CScore for streaming the image

Copyright (c) 2017 - the.RocketRedNeck@gmail.com

RocketRedNeck and MIT Licenses 

RocketRedNeck hereby grants license for others to copy and modify this source code for 
whatever purpose other's deem worthy as long as RocketRedNeck is given credit where 
where credit is due and you leave RocketRedNeck out of it for all other nefarious purposes. 

Permission is hereby granted, free of charge, to any person obtaining a copy 
of this software and associated documentation files (the "Software"), to deal 
in the Software without restriction, including without limitation the rights 
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
copies of the Software, and to permit persons to whom the Software is 
furnished to do so, subject to the following conditions: 

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software. 

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
SOFTWARE. 
**************************************************************************************************** 
"""

# import the necessary packages

# Create arg parser
import argparse
parser = argparse.ArgumentParser()

# Add OPTIONAL IP Address argument
# Specify with "py bucketvision3.py -ip <viewer address> -p <viewer port> "
# viewer address = localhost (default)
# viewer port = 5555 (default)
parser.add_argument('-ip', '--ip-address', required=False, default='localhost', 
help='IP Address Of Viewer')
parser.add_argument('-p', '--port', required=False, default='5555', 
help='IP Address Of Viewer')

# Parse the args
args = vars(parser.parse_args())

import cv2      # OpenCV 4.x
import time
import zmq

# import our classes

from framerate import FrameRate

from bucketcapture import BucketCapture     # Camera capture threads... may rename this
from bucketprocessor import BucketProcessor   # Image processing threads... has same basic structure (may merge classes)
from bucketdisplay import BucketDisplay

    
# Instances of GRIP created pipelines (they usually require some manual manipulation
# but basically we would pass one or more of these into one or more image processors (threads)
# to have their respective process(frame) functions called.
#
# NOTE: NOTE: NOTE:
#
# Still need to work on how unique information from each pipeline is passed around... suspect that it
# will be some context dependent read that is then streamed out for anonymous consumption...
#
#
# NOTE: NOTE: NOTE:
#
# The same pipeline instance should NOT be passed to more than one image processor
# as the results can be confused and comingled and simply does not make sense.

from nada import Nada
from faces import Faces
from findballs import FindBalls

# And so it begins
print("Starting BUCKET VISION!")

# Auto updating listener should be good for avoiding the need to poll for value explicitly
# A ChooserControl is also another option

# NOTE: NOTE: NOTE
#
# For now just create one image pipeline to share with each image processor
# LATER we will modify this to allow for a dictionary (switch-like) interface
# to be injected into the image processors; this will allow the image processors
# to have a selector for exclusion processor of different pipelines
#
# I.e., the idea is to create separate image processors when concurrent pipelines
# are desired (e.g., look for faces AND pink elephants at the same time), and place
# the exclusive options into a single processor (e.g., look for faces OR pink elephants)

nada = Nada()
faces = Faces()
balls = FindBalls()

# NOTE: NOTE: NOTE:
#
# YOUR MILEAGE WILL VARY
# The exposure values are camera/driver dependent and have no well defined standard (i.e., non-portable)
# Our implementation is forced to use v4l2-ctl (Linux) to make the exposure control work because our OpenCV
# port does not seem to play well with the exposure settings (produces either no answer or causes errors depending
# on the camera used)
FRONT_CAM_NORMAL_EXPOSURE = -1
BACK_CAM_NORMAL_EXPOSURE  = -5

width  = 640
height = 480

sources = {'builtin' : 0,
           'usb'     : 1,
           'hdusb'   : '/dev/v4l/by-id/usb-HD_Camera_Manufacturer_HD_USB_Camera-video-index0',
           'usb2.0'  : '/dev/v4l/by-id/usb-HD_Camera_Manufacturer_USB_2.0_Camera-video-index0',
           'p3eye'   : '/dev/v4l/by-id/usb-OmniVision_Technologies__Inc._USB_Camera-B4.09.24.1-video-index0',
           'lifecam' : '/dev/v4l/by-id/usb-Microsoft_Microsoft®_LifeCam_Cinema_TM_-video-index0',
          }

# Declare fps to 30 because explicit is good
frontCam = BucketCapture(name="FrontCam",\
                        src=sources['builtin'],\
                        width=width,\
                        height=height,\
                        exposure=FRONT_CAM_NORMAL_EXPOSURE,\
                        set_fps=30).start()
backCam = BucketCapture(name="BackCam",\
                        src=sources['usb'],\
                        width=width,\
                        height=height,\
                        exposure=BACK_CAM_NORMAL_EXPOSURE,\
                        set_fps=30).start()

print("Waiting for BucketCapture to start...")
while ((frontCam.isStopped() == True)):
    time.sleep(0.001)
while ((backCam.isStopped() == True)):
    time.sleep(0.001)
    
print("BucketCapture appears online!")

# NOTE: NOTE: NOTE
#
# Reminder that each image processor should process exactly one vision pipeline
# at a time (it can be selectable in the future) and that the same vision
# pipeline should NOT be sent to different image processors as this is simply
# confusing and can cause some comingling of data (depending on how the vision
# pipeline was defined... we can't control the use of object-specific internals
# being run from multiple threads... so don't do it!)

pipes = {'nada'  : nada,
         'faces' : faces,
         'balls' : balls}
 
frontProcessor = BucketProcessor(frontCam,pipes,'nada').start()
backProcessor  = BucketProcessor(backCam,pipes,'balls').start()


print("Waiting for BucketProcessors to start...")
while ((frontProcessor.isStopped() == True)):
    time.sleep(0.001)
while ((backProcessor.isStopped() == True)):
    time.sleep(0.001)

print("BucketProcessors appear online!")

# Loop forever displaying the images for initial testing
#
# NOTE: NOTE: NOTE: NOTE:
# cv2.imshow in Linux relies upon X11 binding under the hood. These binding are NOT inherently thread
# safe unless you jump through some hoops to tell the interfaces to operate in a multi-threaded
# environment (i.e., within the same process).
#
# For most purposes, here, we don't need to jump through those hoops or create separate processes and
# can just show the images at the rate of the slowest pipeline plus the speed of the remaining pipelines.
#
# LATER we will create display threads that stream the images as requested at their separate rates.
#

camera = {'frontCam' : frontCam,
          'backCam'  : backCam}
processor = {'frontCam' : frontProcessor,
             'backCam'  : backProcessor}


        
# Start the display loop
print("Waiting for BucketDisplay to start...")
display = BucketDisplay('frontCam', camera, processor).start()
#backDisplay = BucketDisplay('backCam', camera, processor).start()

while (display.isStopped() == True):
    time.sleep(0.001)
#while (backDisplay.isStopped() == True):
    #time.sleep(0.001)

print("Display appears online!")

runTime = 0
nextTime = time.time() + 1

videofile = cv2.VideoWriter('BucketVision.avi',cv2.VideoWriter_fourcc('M','J','P','G'), frontCam.set_fps, (frontCam.width,frontCam.height))

last_count = 0
record = False
stream = False

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.connect('tcp://localhost:5555')

mode = 'frontCam'

while (True):

    if (time.time() > nextTime):
        nextTime = nextTime + 1
        runTime = runTime + 1

    if (type(display.frame) != type(None)):
        if (last_count != display.count):
            last_count = display.count
            if stream == True:
                encoded, buffer = cv2.imencode('.jpg', display.frame)
                socket.send(buffer)

            if record == True:
                videofile.write(display.frame)

        cv2.imshow('main',display.frame)

        key = cv2.waitKey(1)
        if key == ord('r'):
            record = not record
            print("RECORDING = ", record)
        elif key == ord('t'):
            stream = not stream
            print("STREAMING = ", stream)
        elif key == ord('0'):
            mode = 'frontCam'
            display.setmode(mode)
        elif key == ord('1'):
            mode = 'backCam'
            display.setmode(mode)
        else:
            if (mode == 'frontCam'):
                frontCam.processUserCommand(key)
            else:
                backCam.processUserCommand(key)        

        
# NOTE: NOTE: NOTE:
# Sometimes the exit gets messed up, but for now we just don't care

#stop the bucket server and processors

frontProcessor.stop()      # stop this first to make the server exit
#backProcessor.stop()

print("Waiting for BucketProcessors to stop...")
while ((frontProcessor.isStopped() == False)):
    time.sleep(0.001)
#while ((backProcessor.isStopped() == False)):
#    time.sleep(0.001)
print("BucketProcessors appear to have stopped.")

display.stop()
print("Waiting for Display to stop...")
while (display.isStopped() == False):
    time.sleep(0.001)
print("Display appears to have stopped.")


#stop the camera capture
frontCam.stop()
#backCam.stop()

print("Waiting for BucketCaptures to stop...")
while ((frontCam.isStopped() == False)):
    time.sleep(0.001)
# while ((backCam.isStopped() == False)):
#     time.sleep(0.001)
print("BucketCaptures appears to have stopped.")
 
# do a bit of cleanup
cv2.destroyAllWindows()

print("Goodbye!")

