import cv2
import zmq
#import base64
import numpy as np

import sys

context = zmq.Context()
footage_socket = context.socket(zmq.SUB)
footage_socket.bind('tcp://*:5555')
print("Bind Complete")
footage_socket.setsockopt_string(zmq.SUBSCRIBE, np.unicode(''))

footage_socket.RCVTIMEO = 1000 # in milliseconds
count = 0
while True:
    try:
        frame = footage_socket.recv()
#        frame = footage_socket.recv_string()
#        img = base64.b64decode(frame)
#        npimg = np.fromstring(img, dtype=np.uint8)
        npimg = np.fromstring(frame, dtype=np.uint8)
        source = cv2.imdecode(npimg, 1)
#        source = cv2.imdecode(frame, 1)
        cv2.imshow("Stream", source)
        cv2.waitKey(1)

    except KeyboardInterrupt:
        cv2.destroyAllWindows()
        break
    except zmq.error.Again:
        count +=1
        print("Waiting... ", count)
        pass