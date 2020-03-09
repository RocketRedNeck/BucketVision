import threading
import logging

import cv2

try:
	import networktables
except ImportError:
	pass


class Cv2Capture(threading.Thread):
	def __init__(self, camera_num=0, res=(1920, 1080), network_table=None, exposure=None):
		self.logger = logging.getLogger("Cv2Capture{}".format(camera_num))
		self.camera_num = camera_num
		self.net_table = network_table
		self.camera_res = res

		# first vars
		self._exposure = exposure

		self.cap = cv2.VideoCapture(camera_num)
		self.cap_open = self.cap.isOpened()
		if self.cap_open is False:
			self.cap_open = False
			self.write_table_value("Camera{}Status".format(camera_num),
									"Failed to open camera {}!".format(camera_num),
									level=logging.CRITICAL)

		# Threading Locks
		self.capture_lock = threading.Lock()
		self.frame_lock = threading.Lock()

		self._frame = None
		self.new_frame = False

		self.stopped = True

		threading.Thread.__init__(self)

	@property
	def frame(self):
		self.new_frame = False
		# For maximum thread (or process) safety, you should copy the frame, but this is very expensive
		return self._frame

	@property
	def width(self):
		if self.cap_open:
			with self.capture_lock:
				return self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
		else:
			return float("NaN")

	@width.setter
	def width(self, val):
		if val is None:
			return
		if self.cap_open:
			with self.capture_lock:
				self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(val))
			self.write_table_value("Width", int(val))
		else:
			self.write_table_value("Camera{}Status".format(self.camera_num),
									"Failed to set width to {}!".format(val),
									level=logging.CRITICAL)

	@property
	def height(self):
		if self.cap_open:
			with self.capture_lock:
				return self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
		else:
			return float("NaN")

	@height.setter
	def height(self, val):
		if val is None:
			return
		if self.cap_open:
			with self.capture_lock:
				self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(val))
			self.write_table_value("Height", int(val))
		else:
			self.write_table_value("Camera{}Status".format(self.camera_num),
									"Failed to set height to {}!".format(val),
									level=logging.CRITICAL)

	@property
	def exposure(self):
		if self.cap_open:
			with self.capture_lock:
				return self.cap.get(cv2.CAP_PROP_EXPOSURE)
		else:
			return float("NaN")

	@exposure.setter
	def exposure(self, val):
		if val is None:
			return
		self._exposure = int(val)
		if self.cap_open:
			with self.capture_lock:
				self.cap.set(cv2.CAP_PROP_EXPOSURE, int(val))
			self.write_table_value("Exposure", int(val))
		else:
			self.write_table_value("Camera{}Status".format(self.camera_num),
									"Failed to set exposure to {}!".format(val),
									level=logging.CRITICAL)

	def write_table_value(self, name, value, level=logging.DEBUG):
		self.logger.log(level, "{}:{}".format(name, value))
		if self.net_table is None:
			self.net_table = dict()
		if type(self.net_table) is dict:
			self.net_table[name] = value
		else:
			self.net_table.putValue(name, value)

	def stop(self):
		self.stopped = True

	def start(self):
		self.stopped = False
		self.width = self.camera_res[0]
		self.height = self.camera_res[1]
		if self._exposure is None:
			self.exposure = self.exposure
		else:
			self.exposure = self._exposure
		threading.Thread.start(self)

	def run(self):
		img = None
		while not self.stopped:
			# TODO: MAke this less crust, I would like to setup a callback
			try:
				if self._exposure != self.net_table.getEntry("Exposure").value:
					self.exposure = self.net_table.getEntry("Exposure").value
			except:
				pass
			with self.capture_lock:
				_, img = self.cap.read()
			self._frame = img
			self.new_frame = True


if __name__ == '__main__':
	from networktables import NetworkTables
	logging.basicConfig(level=logging.DEBUG)

	NetworkTables.initialize(server='localhost')

	VisionTable = NetworkTables.getTable("BucketVision")
	VisionTable.putString("BucketVisionState", "Starting")
	FrontCameraTable = VisionTable.getSubTable('FrontCamera')

	print("Starting Capture")
	camera = Cv2Capture(network_table=FrontCameraTable)
	camera.start()

	print("Getting Frames")
	while True:
		if camera.new_frame:
			cv2.imshow('my webcam', camera.frame)
		if cv2.waitKey(1) == 27:
			break  # esc to quit
	camera.stop()
