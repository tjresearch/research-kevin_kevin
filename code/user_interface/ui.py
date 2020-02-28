import tkinter as tk
import cv2
import time
import os
import sys
from tkinter import filedialog, simpledialog
from tkinter.messagebox import showerror
from threading import Thread, Event

from PIL import Image, ImageTk

sys.path.insert(1, "../board_detection")
import board_locator

sys.path.insert(1, "../piece_detection")
import identify_pieces

supported_image_formats = [".bmp", ".pbm", ".pgm", ".ppm", ".sr", ".ras", ".jpeg", ".jpg", ".jpe", ".jp2", ".tiff", ".tif", ".png"]
supported_video_formats = [".avi", ".flv", ".wmv", ".mov", ".mp4"]

class Display(tk.Frame):
	def __init__(self, parent):
		self.image_dims = (960, 540)
		self.mode = ""

		self.live_cap = None
		self.live_video_thread = None
		self.live_video_stop = Event()

		self.video_cap = None
		self.video_thread = None
		self.video_stop = Event()
		self.video_play = Event()

		self.display_thread = None
		self.cur_frame = None
		self.display_stop = Event()

		self.intermediate_image_order = ["raw.png",
										 "line_detection.png",
										 "line_linking.png",
										 "lattice_points.png",
										 "board_localization.png",
										 "board_segmentation.png",
										 "piece_classification.png"]
		self.intermediate_image_dir = "./assets/intermediate_images"

		tk.Frame.__init__(self, parent)

		self.button_frame = tk.Frame(self)

		# Initalize the input buttons
		self.side_button_frame = tk.Frame(self.button_frame)
		self.file_button = tk.Button(self.side_button_frame, command=lambda: self.update_display("image"), text="Image", height=3, width=16)
		self.video_button = tk.Button(self.side_button_frame, command=lambda: self.update_display("video"), text="Video", height=3, width=16)
		self.live_video_button = tk.Button(self.side_button_frame, command=lambda: self.update_display("live_video"), text="Live Video", height=3, width=16)

		self.file_button.pack(side=tk.TOP)
		self.video_button.pack(side=tk.TOP)
		self.live_video_button.pack(side=tk.TOP)
		self.side_button_frame.pack(side=tk.TOP)

		# Initialize the buttons to work with the backend
		self.bottom_button_frame = tk.Frame(self.button_frame)
		self.process_button = tk.Button(self.bottom_button_frame, command=self.process, text="Process", height=3, width=16)

		# Initialize the buttons that will tab through intermediate images
		self.nav_button_frame = tk.Frame(self.bottom_button_frame)
		self.back_button = tk.Button(self.nav_button_frame, text="Back", height=2, width=8)
		self.next_button = tk.Button(self.nav_button_frame, text="Next", height=2, width=8)

		self.back_button.pack(side=tk.LEFT)
		self.next_button.pack(side=tk.RIGHT)
		self.nav_button_frame.pack(side=tk.BOTTOM)

		self.process_button.pack(side=tk.TOP)
		self.bottom_button_frame.pack(side=tk.BOTTOM, pady=20)

		self.button_frame.pack(side=tk.LEFT)

		# Intialize the display section
		self.display_frame = tk.Frame(self)

		self.image_label = tk.Label(self.display_frame)
		self.caption = tk.Label(self.display_frame)

		self.show_image("assets/intermediate_images/raw.png")

		self.video_controls = tk.Frame(self.display_frame)
		self.prev_frame_button = tk.Button(self.video_controls, command=self.prev_frame, text="Prev Frame", height=2, width=8)
		self.pause_play_button = tk.Button(self.video_controls, command=self.pause_play, text="Pause/Play", height=2, width=8)
		self.next_frame_button = tk.Button(self.video_controls, command=self.next_frame, text="Next Frame", height=2, width=8)

		self.prev_frame_button.pack(side=tk.LEFT)
		self.pause_play_button.pack(side=tk.LEFT)
		self.next_frame_button.pack(side=tk.LEFT)

		# self.video_controls.pack(side=tk.BOTTOM)

		# Intialize the FEN/PGN display
		self.fen_pgn_label = tk.Label(self, height=25, width=40, padx=20, pady=10, anchor="nw")
		self.fen_pgn_label.configure(font=("Helvetica", 20))

		self.fen_pgn_label.pack(side=tk.RIGHT)

		self.image_label.pack(side=tk.TOP)
		self.caption.pack(side=tk.TOP)
		self.display_frame.pack(side=tk.RIGHT)

		self.pack(fill="both", expand="true", padx=4, pady=4)

		self.start_display()

		# Load models
		self.models_loaded = False
		self.lattice_point_model = None
		self.piece_model = None

		self.model_thread = Thread(target=self.load_models)
		self.model_thread.daemon = True
		self.model_thread.start()

	def load_models(self):
		model_dir = "../models"

		# Load board models
		print("Loading board model...")
		st_load_time = time.time()
		self.lattice_point_model = board_locator.load_model(os.path.join(model_dir, "lattice_points_model.json"),
													   os.path.join(model_dir, "lattice_points_model.h5"))
		print("Loaded in {} s".format(time.time() - st_load_time))

		# Load piece models
		print("Loading piece model...")
		st_load_time = time.time()
		self.piece_model = identify_pieces.local_load_model(os.path.join(model_dir, "piece_detection_model.h5"))
		print("Loaded in {} s".format(time.time() - st_load_time))

		self.models_loaded = True

	def update_display(self, new_mode):
		if not (self.mode == "live_video" and new_mode == "live_video"):
			old_mode = self.mode
			self.mode = new_mode

			if old_mode == "live_video":
				self.live_video_stop.set()
			elif old_mode == "video":
				self.video_controls.pack_forget()
				self.video_stop.set()

			if self.mode == "image":
				file = self.choose_file()
				if file is not None and any(file.endswith(ext) for ext in supported_image_formats):
					self.caption["text"] = file
					self.show_image(file)
			elif self.mode == "video":
				file = self.choose_file()
				if file is not None and any(file.endswith(ext) for ext in supported_video_formats):
					self.start_video(file)
			elif self.mode == "live_video":
				self.start_live_video()

	def show_image(self, image_path):
		load = Image.open(image_path)
		load = load.resize(self.image_dims)
		self.cur_frame = load

	@staticmethod
	def choose_file():
		chosen_file = filedialog.askopenfilename(initialdir = "...", title="Select file")
		if chosen_file:
			return chosen_file
		return None

	def start_live_video(self):
		ip = simpledialog.askstring("IP", "IP Address:")

		url = "http://" + ip + "/live?type=some.mp4"
		self.live_cap = cv2.VideoCapture(url)
		if not self.live_cap.isOpened():
			showerror("Error", "Could not connect capture device at {}".format(ip))
			return
		fps = self.live_cap.get(cv2.CAP_PROP_FPS)
		resolution = (int(self.live_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(self.live_cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
		self.caption["text"] = "IP: {}\nFPS: {}\nResolution {}".format(ip, fps, resolution)

		self.live_video_thread = Thread(target=self.live_video_handler)
		self.live_video_thread.daemon = True
		self.live_video_thread.start()

	def live_video_handler(self):
		try:
			while not self.live_video_stop.is_set():
				ret, frame = self.live_cap.read()
				if ret:
					frame = cv2.resize(frame, self.image_dims)
					disp = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
					self.cur_frame = disp
				else:
					break
		except RuntimeError:
			print("Caught a RuntimeError")
		self.live_cap.release()
		self.live_video_stop.clear()

	def start_display(self):
		self.display_thread = Thread(target=self.display_handler)
		self.display_thread.daemon = True
		self.display_thread.start()

	def display_handler(self):
		while not self.display_stop.is_set():
			render = ImageTk.PhotoImage(self.cur_frame)
			self.image_label.configure(image=render)
			self.image_label.image = render

	def pause_play(self):
		if self.video_play.is_set():
			self.video_play.clear()
		else:
			self.video_play.set()

	def prev_frame(self):
		if not self.video_play.is_set():
			prev_pos = self.video_cap.get(cv2.CAP_PROP_POS_FRAMES) - 2
			if prev_pos >= 0:
				self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, prev_pos)
				self.disp_next_frame()

	def next_frame(self):
		if not self.video_play.is_set():
			self.disp_next_frame()

	def disp_next_frame(self):
		ret, frame = self.video_cap.read()
		if ret:
			frame = cv2.resize(frame, self.image_dims)
			disp = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
			self.cur_frame = disp

	def start_video(self, video_path):
		self.video_controls.pack()
		self.video_cap = cv2.VideoCapture(video_path)
		if not self.video_cap.isOpened():
			showerror("Error", "Could not open video at {}".format(video_path))
			return
		fps = self.video_cap.get(cv2.CAP_PROP_FPS)
		resolution = (int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
		self.caption["text"] = "File: {}\nFPS: {}\nResolution {}".format(video_path, fps, resolution)

		self.video_play.set()
		self.video_thread = Thread(target=self.video_handler, args=(fps,))
		self.video_thread.daemon = True
		self.video_thread.start()

	def video_handler(self, fps):
		try:
			while not self.video_stop.is_set():
				self.video_play.wait()
				ret, frame = self.video_cap.read()
				if ret:
					frame = cv2.resize(frame, self.image_dims)
					disp = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
					self.cur_frame = disp
					time.sleep(1 / fps)
		except RuntimeError:
			print("Caught a RuntimeError")
		self.video_cap.release()
		self.video_stop.clear()

	def process(self):
		if self.models_loaded:
			pass
		else:
			showerror("Error", "Models are still loading, try again in a few seconds.")

	def back(self):
		pass

	def forward(self):
		pass


root = tk.Tk()
root.title("AutoPGN")
disp = Display(root)
root.mainloop()