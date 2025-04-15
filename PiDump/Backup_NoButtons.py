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

# Calculate center offset to align thermal image
offset_x = -3  # Adjust based on physical alignment

# Shared variables
thermal_image = np.zeros((480, 640, 3), dtype=np.uint8)
thermal_array = np.zeros(mlx_shape)  # Store the thermal array for crosshair temperature
lock = threading.Lock()
display_mode = 0  # 0: Normal Camera, 1: Thermal Camera, 2: Fade, 3: Limit
temp_threshold = -40  # Starting temperature threshold
temp_upper_limit = 300  # Default upper limit
temp_lower_limit = -40  # Default lower limit

# Mode names
mode_names = ["Normal", "Thermal", "Fade", "Limit"]

# Function to align and crop thermal data
def align_and_crop(colored_image, array):
    # Calculate cropping box centered on the shifted center
    center_x = mlx_shape[1] // 2 + offset_x
    center_y = mlx_shape[0] // 2
    start_x = max(center_x - cropped_width // 2, 0)
    start_y = max(center_y - cropped_height // 2, 0)
    end_x = min(center_x + cropped_width // 2, mlx_shape[1])
    end_y = min(center_y + cropped_height // 2, mlx_shape[0])

    # Crop the thermal image
    cropped_image = colored_image[start_y:end_y, start_x:end_x]

    # Flip the cropped thermal image vertically
    flipped_image = cv2.flip(cropped_image, 1)

    # Resize the flipped and cropped thermal image to match Pi camera resolution
    resized_image = cv2.resize(flipped_image, (640, 480), interpolation=cv2.INTER_LINEAR)

    # Apply the same cropping to the thermal array (used for masking)
    cropped_array = array[start_y:end_y, start_x:end_x]
    flipped_array = np.flip(cropped_array, axis=1)  # Flip horizontally to match the image
    resized_array = cv2.resize(flipped_array, (640, 480), interpolation=cv2.INTER_LINEAR)

    return resized_image, resized_array

# Function to process MLX90640 thermal data
def process_thermal():
    global thermal_image, thermal_array
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

            # Align and crop the thermal data
            aligned_image, _ = align_and_crop(colored_image, thermal_array)

            # Update the shared thermal image
            with lock:
                thermal_image = aligned_image

        except Exception as e:
            print(f"Thermal processing error: {e}")

# Start thermal processing in a separate thread
thermal_thread = threading.Thread(target=process_thermal, daemon=True)
thermal_thread.start()

# Function to draw text consistently
def draw_text(image, text, position, font=cv2.FONT_HERSHEY_PLAIN, font_scale=1, color=(255, 255, 255), thickness=1):
    cv2.putText(image, text, position, font, font_scale, color, thickness, cv2.LINE_AA)

# Function to draw a crosshair and center temperature
def draw_crosshair_with_temp(image, center_x, center_y, temp, gap=10, size=20, color=(0, 255, 255), thickness=1, alpha=0.5):
    overlay = image.copy()
    # Horizontal line
    cv2.line(overlay, (center_x - size, center_y), (center_x - gap, center_y), color, thickness)
    cv2.line(overlay, (center_x + gap, center_y), (center_x + size, center_y), color, thickness)
    # Vertical line
    cv2.line(overlay, (center_x, center_y - size), (center_x, center_y - gap), color, thickness)
    cv2.line(overlay, (center_x, center_y + gap), (center_x, center_y + size), color, thickness)
    # Add transparency
    cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)
    # Display center temperature near crosshair
    draw_text(image, f"{temp:.1f}C", (center_x - 70, center_y - 20), font_scale=0.5)

# OpenCV fullscreen setup
cv2.namedWindow("Camera Output", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Camera Output", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

while True:
    try:
        # Capture the video frame from the Raspberry Pi camera
        pi_camera_frame = picam2.capture_array()
        pi_camera_frame = cv2.cvtColor(pi_camera_frame, cv2.COLOR_BGR2RGB)

        # Determine the output based on display mode
        with lock:
            center_row = mlx_shape[0] // 2
            center_col = mlx_shape[1] // 2
            center_temp = thermal_array[center_row, center_col]

        if display_mode == 0:  # Normal Camera Output
            output_image = pi_camera_frame
        elif display_mode == 1:  # Thermal Camera Output
            with lock:
                output_image = thermal_image
        elif display_mode == 2:  # Fade (Merged Output)
            with lock:
                # Apply the temperature threshold
                mask = thermal_array > temp_threshold

                # Normalize and apply colormap
                normalized_array = ((thermal_array - np.min(thermal_array)) / (np.max(thermal_array) - np.min(thermal_array)) * 255).astype(np.uint8)
                colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)

                # Align and crop the thermal data
                aligned_image, aligned_array = align_and_crop(colored_image, thermal_array)

                # Apply the mask
                thermal_mask = np.zeros_like(aligned_image)
                thermal_mask[aligned_array > temp_threshold] = aligned_image[aligned_array > temp_threshold]

                # Merge thermal overlay with Pi camera frame
                output_image = cv2.addWeighted(thermal_mask, 0.5, pi_camera_frame, 0.5, 0)

        elif display_mode == 3:  # Limit (Range Overlay)
            with lock:
                # Normalize and apply colormap
                normalized_array = ((thermal_array - np.min(thermal_array)) / (np.max(thermal_array) - np.min(thermal_array)) * 255).astype(np.uint8)
                colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)

                # Align and crop the thermal data
                aligned_image, aligned_array = align_and_crop(colored_image, thermal_array)

                # Apply the range mask
                thermal_mask = np.zeros_like(aligned_image)
                mask = (aligned_array >= temp_lower_limit) & (aligned_array <= temp_upper_limit)
                thermal_mask[mask] = aligned_image[mask]

                # Merge thermal overlay with Pi camera frame
                output_image = cv2.addWeighted(thermal_mask, 0.5, pi_camera_frame, 0.5, 0)

        # Add the crosshair and center temperature to the output image
        center_x = output_image.shape[1] // 2
        center_y = output_image.shape[0] // 2
        draw_crosshair_with_temp(output_image, center_x, center_y, center_temp)

        # Add Set text
        draw_text(output_image, f"Set: {temp_threshold}C", (10, 20), font_scale=0.5)

        # Add Lower and Upper Limit text only in Limit mode
        if display_mode == 3:
            draw_text(output_image, f"Lower: {temp_lower_limit}C", (10, 40), font_scale=0.5)
            draw_text(output_image, f"Upper: {temp_upper_limit}C", (10, 60), font_scale=0.5)

        # Add mode name in the top right corner
        draw_text(output_image, mode_names[display_mode], (500, 20), font_scale=0.5)

        # Display the output
        cv2.imshow("Camera Output", output_image)

        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Quit the program
            break
        elif key == ord('a'):  # Cycle display mode
            display_mode = (display_mode + 1) % 4
        elif key == 81:  # Left arrow key
            temp_threshold = max(-40, temp_threshold - 1)  # Decrease threshold
        elif key == 83:  # Right arrow key
            temp_threshold = min(300, temp_threshold + 1)  # Increase threshold
        elif key == ord('h'):  # Set upper limit
            temp_upper_limit = temp_threshold
        elif key == ord('l'):  # Set lower limit
            temp_lower_limit = temp_threshold

    except Exception as e:
        print(f"Main loop error: {e}")

# Clean up
cv2.destroyAllWindows()
picam2.stop()
