import board
import busio
import adafruit_mlx90640
import time
import numpy as np
import cv2
from picamera2 import Picamera2

# Set up I2C communication for MLX90640
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)

# Initialize MLX90640 sensor
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ  # Set refresh rate

# Create a buffer for the temperatures
mlx_shape = (24, 32)  # 24 rows and 32 columns
frame = [0] * mlx_shape[0] * mlx_shape[1]  # 768 pixels

# Initialize both Pi Cameras
picam0 = Picamera2(0)  # Pi Camera 0
picam1 = Picamera2(1)  # Pi Camera 1 (Rotated)

# Configure cameras
config0 = picam0.create_preview_configuration()
config1 = picam1.create_preview_configuration()

picam0.configure(config0)
picam1.configure(config1)

# Start both cameras
picam0.start()
picam1.start()

# Open a preview window
while True:
    try:
        # Capture frames from both Pi Cameras
        frame0 = picam0.capture_array()
        frame1 = picam1.capture_array()

        # Fix color mapping (Convert BGR to RGB)
        frame0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2RGB)
        frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)

        # Rotate Camera 1 frame 90 degrees clockwise
        #frame1 = cv2.rotate(frame1, cv2.ROTATE_90_CLOCKWISE)

        frame0 = cv2.rotate(frame0, cv2.ROTATE_90_CLOCKWISE)
        # Ensure both Pi Camera frames have the same height
        height = min(frame0.shape[0], frame1.shape[0])
        frame0 = cv2.resize(frame0, (frame0.shape[1], height))
        frame1 = cv2.resize(frame1, (frame1.shape[1], height))

        # Read the MLX90640 temperature data
        mlx.getFrame(frame)

        # Convert temperature values to a NumPy array for image processing
        thermal_array = np.array(frame).reshape(mlx_shape)  # 24x32 array

        # Normalize temperatures to 0-255 for colormap mapping
        min_temp = np.min(thermal_array)
        max_temp = np.max(thermal_array)
        normalized_array = (thermal_array - min_temp) / (max_temp - min_temp) * 255
        normalized_array = normalized_array.astype(np.uint8)

        # Apply colormap (Jet for thermal visualization)
        thermal_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)

        # Resize using Bi-Linear interpolation
        thermal_resized = cv2.resize(thermal_image, (frame0.shape[1], height), interpolation=cv2.INTER_LINEAR)

        # Rotate the thermal image 90 degrees anti-clockwise
        thermal_resized = cv2.rotate(thermal_resized, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Resize the thermal image to match the height of the Pi camera frames
        thermal_resized = cv2.resize(thermal_resized, (thermal_resized.shape[1], height))

        # Combine all three frames horizontally
        combined_frame = np.hstack((frame0, frame1, thermal_resized))

        # Display the combined output
        cv2.imshow("Triple Camera Stream (Pi Cam 0, Pi Cam 1 Rotated, MLX90640 Rotated)", combined_frame)

        # Exit on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Delay to match MLX90640 refresh rate
        time.sleep(0.5)

    except Exception as e:
        print(f"Error reading camera data: {e}")

# Cleanup
cv2.destroyAllWindows()
picam0.close()
picam1.close()

