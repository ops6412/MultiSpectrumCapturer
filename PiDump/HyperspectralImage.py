import board
import busio
import adafruit_mlx90640
import numpy as np
import cv2
from picamera2 import Picamera2

# Set up I2C communication for MLX90640
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)

# Initialize MLX90640 sensor
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

# Create a buffer for the temperatures
mlx_shape = (24, 32)  # 24 rows and 32 columns
frame = [0] * mlx_shape[0] * mlx_shape[1]

# Initialize Pi Cameras
picam0 = Picamera2(0)  # Pi Camera 0
picam1 = Picamera2(1)  # Pi Camera 1

# Capture a single image from both cameras
picam0.start()
picam1.start()
frame0 = picam0.capture_array()
frame1 = picam1.capture_array()
picam0.stop()
picam1.stop()

# Fix color mapping
frame0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2RGB)
frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)

# Rotate Camera 0 frame 90 degrees clockwise
frame0 = cv2.rotate(frame0, cv2.ROTATE_90_CLOCKWISE)

# Determine the target width and height for all images
height = min(frame0.shape[0], frame1.shape[0])
width = min(frame0.shape[1], frame1.shape[1])

# Resize images to match the smallest dimensions
frame0 = cv2.resize(frame0, (width, height))
frame1 = cv2.resize(frame1, (width, height))

# Helper function to align and crop thermal data
def align_and_crop(colored_image, array):
    fov_ratio = 50.0 / 120.0  # Crop from 120-degree FOV to 50-degree FOV
    cropped_width = int(mlx_shape[1] * fov_ratio)
    cropped_height = int(mlx_shape[0] * fov_ratio)
    offset_x = 1 #Adjust horizontal offset
    offset_y = 1  # Move image center down by 10cm
    center_x = mlx_shape[1] // 2 + offset_x
    center_y = mlx_shape[0] // 2 + offset_y
    start_x = max(center_x - cropped_width // 2, 0)
    start_y = max(center_y - cropped_height // 2, 0)
    end_x = min(center_x + cropped_width // 2, mlx_shape[1])
    end_y = min(center_y + cropped_height // 2, mlx_shape[0])

    cropped_image = colored_image[start_y:end_y, start_x:end_x]
    flipped_image = cv2.flip(cropped_image, 1)
    resized_image = cv2.resize(flipped_image, (width, height), interpolation=cv2.INTER_LINEAR)

    cropped_array = array[start_y:end_y, start_x:end_x]
    flipped_array = np.flip(cropped_array, axis=1)
    resized_array = cv2.resize(flipped_array, (width, height), interpolation=cv2.INTER_LINEAR)

    return resized_image, resized_array

# Capture MLX90640 temperature data
mlx.getFrame(frame)
thermal_array = np.array(frame).reshape(mlx_shape)
min_temp = np.min(thermal_array)
max_temp = np.max(thermal_array)
normalized_array = ((thermal_array - min_temp) / (max_temp - min_temp) * 255).astype(np.uint8)
thermal_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)
thermal_resized, thermal_array = align_and_crop(thermal_image, thermal_array)
thermal_resized = cv2.rotate(thermal_resized, cv2.ROTATE_90_CLOCKWISE)

# Initialize visibility and opacity
visibility = {'frame0': True, 'frame1': False, 'thermal': False}
opacity = {'frame0': 1.0, 'frame1': 1.0, 'thermal': 1.0}

def update_display():
    overlay = np.zeros((height, width, 3), dtype=np.float32)
    if visibility['frame0']:
        overlay += (frame0.astype(np.float32) * opacity['frame0'])
    if visibility['frame1']:
        overlay += (frame1.astype(np.float32) * opacity['frame1'])
    if visibility['thermal']:
        overlay += (thermal_resized.astype(np.float32) * opacity['thermal'])
    overlay = np.clip(overlay, 0, 255).astype(np.uint8)
    
    # Overlay control text in the top-left corner
    cv2.putText(overlay, "Press 1: Toggle Pi Cam 0", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
    cv2.putText(overlay, "Press 2: Toggle Pi Cam 1", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
    cv2.putText(overlay, "Press 3: Toggle Thermal", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
    cv2.imshow("Overlayed Images & Controls", overlay)

def toggle_frame(frame):
    visibility[frame] = not visibility[frame]
    update_display()

def adjust_opacity(frame, delta):
    opacity[frame] = max(0.0, min(1.0, opacity[frame] + delta))
    update_display()

update_display()

while True:
    key = cv2.waitKey(0) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('1'):
        toggle_frame('frame0')
    elif key == ord('2'):
        toggle_frame('frame1')
    elif key == ord('3'):
        toggle_frame('thermal')
    elif key == ord('w'):
        adjust_opacity('frame0', 0.1)
    elif key == ord('s'):
        adjust_opacity('frame0', -0.1)
    elif key == ord('e'):
        adjust_opacity('frame1', 0.1)
    elif key == ord('d'):
        adjust_opacity('frame1', -0.1)
    elif key == ord('r'):
        adjust_opacity('thermal', 0.1)
    elif key == ord('f'):
        adjust_opacity('thermal', -0.1)

cv2.destroyAllWindows()