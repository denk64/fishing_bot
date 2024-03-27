import tkinter as tk
from tkinter import Canvas, Entry, Label, Button
from threading import Thread
from PIL import Image, ImageGrab, ImageTk
from screeninfo import get_monitors
import requests
import base64
import time
import io
from pygame import mixer
import pickle
import pyautogui
import random
import numpy as np
import cv2
from collections import deque
from datetime import datetime
import os
from yolo_inference import YoloInference
from mss import mss


class App:
    SETTINGS_FILE = 'app_settings.pkl'
    BUFFER_SIZE = 5  # 5 seconds of vid


    pyautogui.FAILSAFE = False


    def __init__(self, root):
        self.root = root
        self.root.title("Bob The Fisherman")

        self.last_detected_time = time.time()
        self.last_levitate_buff = time.time()
        self.last_open_shell_time = time.time()
        self.last_mackarel_time = time.time()
        self.time_since_startet_to_fish = time.time()
        self.last_detected_timeout = time.time()
        self.detection_times = []
        self.last_sold_items = time.time()


        # Bind the on_closing method to the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        fishing_started = False
        self.time_left = None


        self.running = False
        self.tk_image = None

        # Initialize the mixer
        mixer.init()

        # Load sound
        self.alert_sound = mixer.Sound('pop_sound.mp3')

        # Start Button
        self.start_button = Button(root, text="Start", command=self.start, bg="SystemButtonFace")
        self.start_button.pack(pady=10)

        # A circle to show if the api is running anchored to the top right corner
        self.api_circle = Canvas(root, bg="white", width=20, height=20)
        self.api_circle.pack(pady=20)
        self.api_circle.create_oval(5, 5, 20, 20, fill="red", outline="red")
        self.api_circle.place(relx=1.0, rely=0.0, anchor='ne')

        # Stop Button
        self.stop_button = Button(root, text="Stop", command=self.stop, bg="SystemButtonFace", state="disabled")
        self.stop_button.pack(pady=10)

        # # Upload Button
        # self.upload_button = Button(root, text="Upload Image", command=self.upload_image)
        # self.upload_button.pack(pady=10)

        # Monitor selection
        self.monitors = get_monitors()
        self.monitor_var = tk.StringVar(root)
        self.monitor_var.set(self.monitors[0].name)
        self.monitor_dropdown = tk.OptionMenu(root, self.monitor_var, *[monitor.name for monitor in self.monitors])
        self.monitor_dropdown.pack(pady=10)

        # button to take a screenshot and draw on the canvas
        self.screenshot_button = Button(root, text="Take Screenshot", command=self.display_image)
        self.screenshot_button.pack(pady=10)

        # Canvas for image preview
        self.canvas_width = 300  # You can adjust this
        self.canvas = Canvas(root, bg="white", width=self.canvas_width, height=self.canvas_width)  # Default height
        self.canvas.pack(pady=20)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.selection_rectangle = None
        self.start_x = None
        self.start_y = None

        # FPS Input
        self.fps_label = Label(root, text="FPS:")
        self.fps_label.pack(pady=5)
        self.fps_entry = Entry(root)
        self.fps_entry.pack(pady=5)
        self.fps_confirm_button = Button(root, text="Set FPS", command=self.set_fps)
        self.fps_confirm_button.pack(pady=10)
        self.fps = 1  # Default

        # Confidence threshold but times 100
        self.confidence_label = Label(root, text="Confidence:")
        self.confidence_label.pack(pady=5)
        self.confidence_entry = Entry(root)
        self.confidence_entry.pack(pady=5)
        self.confidence_confirm_button = Button(root, text="Set Confidence", command=self.set_confidence)
        self.confidence_confirm_button.pack(pady=10)
        self.confidence = 50  # Default 50%







        # # Checkbox for recording
        # self.recording_var = tk.IntVar()
        # self.record_checkbox = tk.Checkbutton(root, text="Enable Recording", variable=self.recording_var)
        # self.record_checkbox.pack(pady=10)

        # # Checkbox for logout/login
        # self.logout_login_var = tk.IntVar()
        # self.logout_login_checkbox = tk.Checkbutton(root, text="Enable Logout/Login", variable=self.logout_login_var)
        # self.logout_login_checkbox.pack(pady=10)

        # # Timer for logout/login with set button
        # self.timer_label = Label(root, text="Time to Logout/Login in minutes:")
        # self.timer_label.pack(pady=5)
        # self.timer_entry = Entry(root)
        # self.timer_entry.pack(pady=5)
        # self.timer_confirm_button = Button(root, text="Set Timer", command=self.set_timer)
        # self.timer_entry.insert(0, "60")
        # self.timer_confirm_button.pack(pady=10)
        # self.timer = 60  # Default

        # self.countdown_label = tk.Label(self.root, text="Countdown: Not Started")
        # self.countdown_label.pack()  # or however you position your widgets

        
        # Initialize buffer
        self.frame_buffer = deque(maxlen=int(self.BUFFER_SIZE * self.fps))

        self.volume_label = Label(root, text="Volume:")
        self.volume_label.pack(pady=5)
        self.volume_slider = tk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, command=self.update_volume)
        self.volume_slider.set(40)  # Default value (0.4 * 100)
        self.volume_slider.pack(pady=5)

        # Try to load settings
        self.load_settings()

        self.inferencer = YoloInference()


    def on_closing(self):
        """Handle the event when the main window is closed."""
        self.save_settings()
        self.root.destroy()

    def load_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'rb') as f:
                settings = pickle.load(f)
                
                self.fps = settings['fps']
                self.fps_entry.insert(0, str(self.fps))

                self.confidence = settings['confidence']
                self.confidence_entry.insert(0, str(self.confidence))

                
                self.monitor_var.set(settings['monitor'])

                self.volume_slider.set(settings['volume'] * 100)
                

                # if 'selection_coords' in settings:
                #     coords = settings['selection_coords']
                #     self.selection_rectangle = self.canvas.create_rectangle(*coords, outline="red", width=2)

        except (FileNotFoundError, pickle.UnpicklingError, KeyError):
            # If there's any issue loading, just continue with defaults
            pass

    def save_settings(self):
        settings = {
            'fps': self.fps,
            'confidence': self.confidence,
            'monitor': self.monitor_var.get(),
            'volume': self.volume_slider.get() / 100
        }
        # if self.selection_rectangle:
        #     settings['selection_coords'] = self.canvas.coords(self.selection_rectangle)

        with open(self.SETTINGS_FILE, 'wb') as f:
            pickle.dump(settings, f)

    # def upload_image(self):
    #     file_path = filedialog.askopenfilename()
    #     if file_path:
    #         self.original_image = Image.open(file_path)
    #         self.display_image()

    def display_image(self):

        # get screenshoot of the character menu
        img = self.get_screenshot_from_selected_monitor()



        self.image_aspect_ratio = img.width / img.height
        self.canvas_height = int(self.canvas_width / self.image_aspect_ratio)
        self.canvas.config(width=self.canvas_width, height=self.canvas_height)
        self.tk_image = ImageTk.PhotoImage(img.resize((self.canvas_width, self.canvas_height)))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        if self.selection_rectangle:
            self.canvas.tag_raise(self.selection_rectangle)

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

        if not self.selection_rectangle:
            self.selection_rectangle = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

    def on_mouse_drag(self, event):
        self.canvas.coords(self.selection_rectangle, self.start_x, self.start_y, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def on_button_release(self, event):
        pass

    def set_fps(self):
        try:
            self.fps = float(self.fps_entry.get())
        except ValueError:
            print("Invalid FPS value. Using default.")

    def set_confidence(self): # confidence is an int from 0 to 100
        try:
            self.confidence = int(self.confidence_entry.get())
            print(self.confidence)
        except ValueError:
            print("Invalid Confidence value. Using default.")



    def set_timer(self):
        try:
            self.timer = float(self.timer_entry.get())
        except ValueError:
            print("Invalid Timer value. Using default.")

    def get_screenshot(self):
        monitor = [m for m in self.monitors if m.name == self.monitor_var.get()][0]
        coordinates = self.canvas.coords(self.selection_rectangle)
        # Map from resized image to original image
        left, top, right, bottom = (coordinates[0] * monitor.width / self.canvas_width,
                                    coordinates[1] * monitor.height / self.canvas_height,
                                    coordinates[2] * monitor.width / self.canvas_width,
                                    coordinates[3] * monitor.height / self.canvas_height)
        img = ImageGrab.grab(bbox=(left, top, right, bottom))
        return img
    

    def get_screenshot_from_selected_monitor(self):
        with mss() as sct:
            monitor_number = 1  # Change this to the correct monitor number (1 for primary)
            monitor = sct.monitors[monitor_number]
            sct_img = sct.grab(monitor)
            img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
            return img

    def image_to_base64(self, image):
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def send_image_to_api_(self, image):
        try:

            image_data = self.image_to_base64(image)
            api_url = "http://192.168.1.16:8888/predict/"
            response = requests.post(api_url, json={"base64_str": image_data})
            if response.status_code == 200:
                # Change the color of the circle to green
                self.api_circle.create_oval(5, 5, 20, 20, fill="green", outline="green")
                return response.json()

            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return None
        except:
            print("Error: Could not connect to API")
            # Change the color of the circle to red
            self.api_circle.create_oval(5, 5, 20, 20, fill="red", outline="red")
            return None
        
    def send_image_to_api(self, image):
        # convert the image from PIL/Pillow to OpenCV format
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # run inference on the image and return the labels
        labels = self.inferencer.get_labels([image])
        return labels

        
    def send_image_to_api_button(self, image):
        image_data = self.image_to_base64(image)
        api_url = "http://192.168.1.16:8888/button/"
        response = requests.post(api_url, json={"base64_str": image_data})
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
        
    def logout_login(self):
        #use pyautogui to press enter and write /logout
        self.countdown_label.config(text=f"Relog Started - Please wait")
        print("Logging out and in...")
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(1)
        pyautogui.write('/logout')
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(25)
        #send a full screenshot to the api and get respones with the coordinates of the button
        img = self.get_screenshot_char_menu()
        results = self.send_image_to_api_button(img)
        if results:
            detections = results.get("detections", [])
            class_ids = [detection.get("class_id") for detection in detections]
            #if class_id 0 is detected, move the mouse to the middle of its box
            for detection in detections:
                if detection.get("class_id") == 0:
                    coords = detection.get("coordinates")
                    if coords:
                        #get current mouse coordinates
                        x, y = pyautogui.position()
                        #map the coordinates from the detection relative to the original monitor coordinates
                        x_center = coords["xmin"] + (coords["xmax"] - coords["xmin"]) / 2
                        y_center = coords["ymin"] + (coords["ymax"] - coords["ymin"]) / 2
                        pyautogui.moveTo(x_center, y_center)
                        time.sleep(0.1)
                        pyautogui.click(button='left')
                        time.sleep(0.1)
                        pyautogui.moveTo(x, y)
                        time.sleep(10)
                        break


        
    def update_volume(self, value):
        volume = float(value) / 100
        self.alert_sound.set_volume(volume)

    def save_buffer_to_file(self):
        # 3 seconds before and 2 seconds after the signal
        record_duration = 3
        record_frames = int(record_duration * self.fps)
        frames_to_save = list(self.frame_buffer)[-record_frames:]
        if not frames_to_save:
            print("No frames to save!")
            return
        
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(f'avi/recorded_{datetime.now().strftime("%Y%m%d_%H%M%S")}.avi', fourcc, self.fps, frames_to_save[0][0].size)

        for frame, _ in frames_to_save:
            out.write(cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR))
        out.release()

    def worker(self):
        self.fishing_started = True
        fish_caught = False

        self.time_since_startet_to_fish = time.time()

        while self.running:


            #if keyboard.is_pressed('page up'):
                #self.save_buffer_to_file()

            # Get current timestamp
            current_timestamp = datetime.now()
            
            # Get screen image
            img = self.get_screenshot()

            # If recording is enabled, append to buffer
            # if self.recording_var.get() == 1:
            #     self.frame_buffer.append((img, current_timestamp))
            #     # Ensure the buffer doesn't exceed its size limit
            #     while len(self.frame_buffer) > self.BUFFER_SIZE * self.fps:
            #         self.frame_buffer.pop(0)

            results = self.send_image_to_api(img)

            #detections = results.get("detections", [])
            #class_ids = [detection.get("class_id") for detection in detections]
            monitor = [m for m in self.monitors if m.name == self.monitor_var.get()][0]

            # Get the region selected on the monitor
            coordinates = self.canvas.coords(self.selection_rectangle)
            left, top, right, bottom = (coordinates[0] * monitor.width / self.canvas_width,
                                        coordinates[1] * monitor.height / self.canvas_height,
                                        coordinates[2] * monitor.width / self.canvas_width,
                                        coordinates[3] * monitor.height / self.canvas_height)
            
            # If class_id 0 is detected, move the mouse to the middle of its box
            for label in results:
                coordinates, class_name, confidence = label.split(',')

                # Clean and parse the data
                coordinates = coordinates.strip('[]').split()
                x1_, y1_, x2_, y2_ = map(float, coordinates)  # Convert string coordinates to float
                class_name = class_name.strip()
                confidence = float(confidence.strip())  # Convert confidence string to float

                #print(f"Confidence: {confidence} - Class: {class_name}")

                # Confidence threshold from the UI


                if class_name == 'fish' and confidence >= self.confidence / 100:

                    self.last_detected_timeout = time.time()

                    # Clear detections older than 2 seconds
                    self.detection_times = [t for t in self.detection_times if time.time() - t <= 2]

                    # If class_id 0 is detected at least 2 times in 2 seconds, execute action

                    random_number_time = random.uniform(0.8, 1.9)
                    random_number_time2 = random.uniform(0.5, 0.9)
                    random_number_coord = random.randint(1, 20)

                    self.alert_sound.play()

                    # Get current mouse coordinates
                    x, y = pyautogui.position()
                    if coordinates:
                        # Calculate the center of the detected bounding box
                        x_center = x1_ + (x2_ - x1_) / 2
                        y_center = y1_  + (y2_ - y1_) / 2

                        # Map the coordinates from the detection relative to the original monitor coordinates
                        x_center += left
                        y_center += top
                        pyautogui.moveTo(x_center, y_center)
                        fish_caught = True
                        # time.sleep(0.3)
                        pyautogui.click(button='right')
                        # time.sleep(0.8)
                        pyautogui.moveTo(x, y)
                        # time.sleep(random_number_time2 + random_number_time2)
                        # if self.recording_var.get() == 1:
                        #     self.save_buffer_to_file()

                        # Reset the detection_times list
                        self.detection_times.clear()

                        break  # If there are multiple class_id 0 detections, we'll just use the first one
                
                elif class_name == "no_fish":
                    self.last_detected_time = time.time()
                    self.last_detected_timeout = time.time()

            # if time since last mackarel buff is greater than 5 minutes, press the insert key then update time
            if time.time() - self.last_mackarel_time >= 20 and fish_caught == True:
                pyautogui.press('pageup')
                self.last_mackarel_time = time.time()
                
            # if time since last levitate buff is greater than 10 minutes press home key then update time
            if time.time() - self.last_levitate_buff >= 580 and fish_caught == True:
                pyautogui.press('home')
                time.sleep(4)
                self.last_levitate_buff = time.time()

            if time.time() - self.last_open_shell_time >= 10 and fish_caught == True:
                pyautogui.press('insert')
                self.last_open_shell_time = time.time()

            if time.time() - self.last_sold_items >= 1800 and fish_caught == True:
                # press numpad 1 to mount
                pyautogui.press('num1')
                # wait to mount
                time.sleep(3)
                # press numpad 2 to target the vendor
                pyautogui.press('num2')
                # wait 1 sec
                time.sleep(1)
                # press page down to sell
                pyautogui.press('pagedown')
                # wait 10 seconds
                time.sleep(10)
                # press numpad 1 to dismount
                pyautogui.press('num1')

                self.last_sold_items = time.time()

            # if time.time() - self.last_detected_timeout >= 580:
            #     os._exit(0)

            # If Logout/Login is enabled, check if it's time to logout/login in minutes
            # if self.logout_login_var.get() == 1:
            #     elapsed_time = time.time() - self.time_since_startet_to_fish
            #     self.time_left = int(self.timer * 60 - elapsed_time)
            #     minutes, seconds = divmod(self.time_left, 60)
            #     self.countdown_label.config(text=f"Countdown: {minutes}m {seconds}s")
            #     if time.time() - self.time_since_startet_to_fish >= int(self.timer) * 60:
            #         self.logout_login()
            #         self.time_since_startet_to_fish = time.time()
            # else:
            #     self.countdown_label.config(text="Countdown: Not Started")
            # If class_id 1 or 0 are not detected for 5 seconds, press the home key
            if fish_caught or (time.time() - self.last_detected_time >= 5):
                self.last_detected_time = time.time()
                time.sleep(0.1)
                fish_caught = False
                pyautogui.press('end')
                time.sleep(2)



            time.sleep(1.0 / self.fps)


    def start(self):
        if not self.running:
            self.running = True
            self.worker_thread = Thread(target=self.worker)
            self.worker_thread.start()
            self.start_button.configure(bg="light green")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")


    def stop(self):
        # Kill the worker thread
        if self.running:
            self.running = False
            self.worker_thread.join(0.1)

            self.start_button.configure(bg="SystemButtonFace")
            self.stop_button.configure(state="disabled")
            self.start_button.configure(state="normal")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    app.run()