#import base64
import cv2
import zmq

context = zmq.Context()
footage_socket = context.socket(zmq.PUB)
footage_socket.connect('tcp://localhost:5555')

camera = cv2.VideoCapture(1)  # init the camera

count = 0
while True:
    try:
        grabbed, frame = camera.read()  # grab the current frame
        frame = cv2.resize(frame, (640, 480))  # resize the frame
        encoded, buffer = cv2.imencode('.jpg', frame)
        # jpg_as_text = base64.b64encode(buffer)
        # footage_socket.send(jpg_as_text)
        footage_socket.send(buffer)
        count += 1
        print("Sending ", count)

    except KeyboardInterrupt:
        camera.release()
        cv2.destroyAllWindows()
        break