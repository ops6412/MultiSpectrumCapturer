import cv2
import numpy as np
import time
import RPi.GPIO as GPIO
from picamera2 import Picamera2

# GPIO Pins for camera selection (check your Arducam documentation)
SEL_PINS = [17, 27]  # For example, these control cam0, cam1, cam2 (binary encoding)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
for pin in SEL_PINS:
    GPIO.setup(pin, GPIO.OUT)

def select_camera(index):
    # Convert index to binary and set GPIOs
    binary = format(index, f'0{len(SEL_PINS)}b')
    for i, bit in enumerate(binary):
        GPIO.output(SEL_PINS[i], int(bit))
    time.sleep(0.2)  # Small delay to allow switching

# Initialize camera
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()
time.sleep(1)

frames = []

# Capture from each camera
for cam_index in range(3):
    select_camera(cam_index)
    frame = picam2.capture_array()
    frames.append(frame)

# Release resources
picam2.stop()
GPIO.cleanup()

# Stitch side-by-side
stitched = np.hstack(frames)
cv2.imshow("Three Camera Views", stitched)
cv2.waitKey(0)
cv2.destroyAllWindows()
