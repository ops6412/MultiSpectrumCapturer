import board
import busio
import adafruit_mlx90640
import time
import numpy as np
import cv2
from picamera2 import Picamera2
import math

# Set up I2C communication for MLX90640
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)

# Initialize MLX90640 sensor
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ  # Set the refresh rate

# Create a buffer for the temperatures
mlx_shape = (24, 32)  # 24 rows and 32 columns
frame = [0] * mlx_shape[0] * mlx_shape[1]  # 768 pixels

# Define the temperature range (in Celsius) for yellow coloring
lower_limit = 25.0  # Lower limit for yellow color
upper_limit = 40.0  # Upper limit for yellow color

# Initialize the Raspberry Pi camera (PiCamera2)
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()

# Set the opacity values for both images (0.0 to 1.0)
thermal_opacity = 0.5  # Opacity for the thermal camera overlay
camera_opacity = 0.5  # Opacity for the Pi camera

# Calculate crop size for 50-degree FOV from 110-degree thermal FOV
fov_ratio = 50.0 / 110.0
cropped_width = int(mlx_shape[1] * fov_ratio)  # Width in pixels
cropped_height = int(mlx_shape[0] * fov_ratio)  # Height in pixels

# Calculate center offset to align thermal image (shift left by 5 pixels for 10mm separation)
offset_x = -5

while True:
    try:
        # Read the temperature data from the MLX90640 sensor
        mlx.getFrame(frame)

        # Convert the temperature values to a NumPy array for image processing
        thermal_array = np.array(frame).reshape(mlx_shape)  # 24x32 array

        # Create an empty image (24x32 in 3 channels for BGR format)
        image = np.zeros((mlx_shape[0], mlx_shape[1], 3), dtype=np.uint8)

        # Apply color based on temperature range
        for y in range(mlx_shape[0]):  # rows
            for x in range(mlx_shape[1]):  # columns
                temp = thermal_array[y, x]
                if lower_limit <= temp <= upper_limit:
                    image[y, x] = (0, 255, 255)  # Yellow in BGR
                else:
                    image[y, x] = (255, 0, 0)  # Blue in BGR

        # Calculate cropping box centered on the shifted center
        center_x = mlx_shape[1] // 2 + offset_x
        center_y = mlx_shape[0] // 2
        start_x = max(center_x - cropped_width // 2, 0)
        start_y = max(center_y - cropped_height // 2, 0)
        end_x = min(center_x + cropped_width // 2, mlx_shape[1])
        end_y = min(center_y + cropped_height // 2, mlx_shape[0])

        # Crop the thermal image for a 50-degree FOV
        cropped_image = image[start_y:end_y, start_x:end_x]

        # Flip the cropped thermal image vertically
        flipped_image = cv2.flip(cropped_image, 1)

        # Resize the flipped and cropped thermal image to match Pi camera resolution
        thermal_resized = cv2.resize(flipped_image, (640, 480), interpolation=cv2.INTER_NEAREST)

        # Capture the video frame from the Raspberry Pi camera
        pi_camera_frame = picam2.capture_array()
        pi_camera_frame = cv2.cvtColor(pi_camera_frame, cv2.COLOR_BGR2RGB)  # Convert from BGR to RGB

        # Resize the Pi camera frame to ensure same resolution (640x480)
        pi_camera_frame = cv2.resize(pi_camera_frame, (640, 480))

        # Blend the resized thermal image and Pi camera frame using opacity settings
        blended_image = cv2.addWeighted(thermal_resized, thermal_opacity, pi_camera_frame, camera_opacity, 0)

        # Show the blended image in a window
        cv2.imshow("Blended Thermal and Pi Camera Output", blended_image)

        # Wait for a short period (or break on key press)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Optional: Add a small delay to avoid overwhelming the processing
        time.sleep(0.5)

    except Exception as e:
        print(f"Error reading MLX90640 data: {e}")

# Close the OpenCV window and stop Pi camera
cv2.destroyAllWindows()
picam2.stop()
