import board
import busio
import adafruit_mlx90640
import numpy as np
import cv2
from picamera2 import Picamera2
import threading

# Set up I2C communication for MLX90640
i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)  # Increased baud rate to 1 MHz

# Initialize MLX90640 sensor
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_8_HZ  # Max refresh rate

# Create a buffer for the temperatures
mlx_shape = (24, 32)  # 24 rows and 32 columns
frame = [0] * mlx_shape[0] * mlx_shape[1]  # 768 pixels

# Initialize the Raspberry Pi camera (PiCamera2)
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

# Calculate crop size for 50-degree FOV from 110-degree thermal FOV
fov_ratio = 50.0 / 110.0
cropped_width = int(mlx_shape[1] * fov_ratio)  # Width in pixels
cropped_height = int(mlx_shape[0] * fov_ratio)  # Height in pixels

# Calculate center offset to align thermal image (shift left by 5 pixels for 10mm separation)
offset_x = -3

# Shared variables
thermal_image = np.zeros((480, 640, 3), dtype=np.uint8)
lock = threading.Lock()
display_mode = 0  # 0: Normal Camera, 1: Thermal Camera, 2: Merged Output

# Function to process MLX90640 thermal data
def process_thermal():
    global thermal_image
    while True:
        try:
            # Read the thermal data
            mlx.getFrame(frame)
            thermal_array = np.array(frame).reshape(mlx_shape)

            # Normalize and apply colormap
            min_temp = np.min(thermal_array)
            max_temp = np.max(thermal_array)
            normalized_array = ((thermal_array - min_temp) / (max_temp - min_temp) * 255).astype(np.uint8)
            colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)

            # Calculate cropping box centered on the shifted center
            center_x = mlx_shape[1] // 2 + offset_x
            center_y = mlx_shape[0] // 2
            start_x = max(center_x - cropped_width // 2, 0)
            start_y = max(center_y - cropped_height // 2, 0)
            end_x = min(center_x + cropped_width // 2, mlx_shape[1])
            end_y = min(center_y + cropped_height // 2, mlx_shape[0])

            # Crop the thermal image for a 50-degree FOV
            cropped_image = colored_image[start_y:end_y, start_x:end_x]

            # Flip the cropped thermal image vertically
            flipped_image = cv2.flip(cropped_image, 1)

            # Resize the flipped and cropped thermal image to match Pi camera resolution using Bi-Linear interpolation
            thermal_resized = cv2.resize(flipped_image, (640, 480), interpolation=cv2.INTER_LINEAR)

            # Update the shared thermal image
            with lock:
                thermal_image = thermal_resized

        except Exception as e:
            print(f"Thermal processing error: {e}")

# Start thermal processing in a separate thread
thermal_thread = threading.Thread(target=process_thermal, daemon=True)
thermal_thread.start()

while True:
    try:
        # Capture the video frame from the Raspberry Pi camera
        pi_camera_frame = picam2.capture_array()
        pi_camera_frame = cv2.cvtColor(pi_camera_frame, cv2.COLOR_BGR2RGB)

        # Determine the output based on display mode
        if display_mode == 0:  # Normal Camera Output
            output_image = pi_camera_frame
        elif display_mode == 1:  # Thermal Camera Output
            with lock:
                output_image = thermal_image
        elif display_mode == 2:  # Merged Output
            with lock:
                output_image = cv2.addWeighted(thermal_image, 0.5, pi_camera_frame, 0.5, 0)

        # Display the output
        cv2.imshow("Camera Output", output_image)

        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Quit the program
            break
        elif key == ord('a'):  # Cycle display mode
            display_mode = (display_mode + 1) % 3

    except Exception as e:
        print(f"Main loop error: {e}")

# Clean up
cv2.destroyAllWindows()
picam2.stop()
