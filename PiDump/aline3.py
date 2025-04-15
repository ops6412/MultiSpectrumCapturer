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

# Shared variables
thermal_image = np.zeros((480, 640, 3), dtype=np.uint8)
thermal_array = np.zeros(mlx_shape)  # Store the thermal array for crosshair temperature
lock = threading.Lock()
display_mode = 0  # 0: Normal Camera, 1: Thermal Camera, 2: Merged Output, 3: Range Overlay
temp_threshold = -40  # Starting temperature threshold
temp_upper_limit = 300  # Default upper limit
temp_lower_limit = -40  # Default lower limit

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

            # Resize and flip the image for display
            resized_image = cv2.resize(colored_image, (640, 480), interpolation=cv2.INTER_LINEAR)
            flipped_image = cv2.flip(resized_image, 1)

            # Update the shared thermal image
            with lock:
                thermal_image = flipped_image

        except Exception as e:
            print(f"Thermal processing error: {e}")

# Start thermal processing in a separate thread
thermal_thread = threading.Thread(target=process_thermal, daemon=True)
thermal_thread.start()

# Function to draw a crosshair
def draw_crosshair(image, center_x, center_y, gap=10, size=20, color=(0, 255, 255), thickness=1, alpha=0.5):
    overlay = image.copy()
    # Horizontal line
    cv2.line(overlay, (center_x - size, center_y), (center_x - gap, center_y), color, thickness)
    cv2.line(overlay, (center_x + gap, center_y), (center_x + size, center_y), color, thickness)
    # Vertical line
    cv2.line(overlay, (center_x, center_y - size), (center_x, center_y - gap), color, thickness)
    cv2.line(overlay, (center_x, center_y + gap), (center_x, center_y + size), color, thickness)
    # Add transparency
    cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

while True:
    try:
        # Capture the video frame from the Raspberry Pi camera
        pi_camera_frame = picam2.capture_array()
        pi_camera_frame = cv2.cvtColor(picam2.capture_array(), cv2.COLOR_BGR2RGB)

        # Determine the output based on display mode
        if display_mode == 0:  # Normal Camera Output
            output_image = pi_camera_frame
        elif display_mode == 1:  # Thermal Camera Output
            with lock:
                output_image = thermal_image
        elif display_mode == 2:  # Merged Output
            with lock:
                # Filter the thermal image by threshold
                mask = thermal_array > temp_threshold

                # Normalize and apply colormap
                normalized_array = ((thermal_array - np.min(thermal_array)) / (np.max(thermal_array) - np.min(thermal_array)) * 255).astype(np.uint8)
                colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)

                # Create a mask for areas above the threshold
                thermal_mask = np.zeros_like(colored_image)
                thermal_mask[mask] = colored_image[mask]

                # Resize and flip the thermal mask
                resized_thermal = cv2.resize(thermal_mask, (640, 480), interpolation=cv2.INTER_LINEAR)
                flipped_thermal = cv2.flip(resized_thermal, 1)

                # Merge thermal overlay with Pi camera frame
                output_image = cv2.addWeighted(flipped_thermal, 0.5, pi_camera_frame, 0.5, 0)

                # Display the current threshold value
                cv2.putText(output_image, f"Set: {temp_threshold}C", (10, 30),
                            cv2.FONT_HERSHEY_DUPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

        elif display_mode == 3:  # Range Overlay
            with lock:
                # Filter the thermal image by range
                mask = (thermal_array >= temp_lower_limit) & (thermal_array <= temp_upper_limit)

                # Normalize and apply colormap
                normalized_array = ((thermal_array - np.min(thermal_array)) / (np.max(thermal_array) - np.min(thermal_array)) * 255).astype(np.uint8)
                colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)

                # Create a mask for areas within the range
                thermal_mask = np.zeros_like(colored_image)
                thermal_mask[mask] = colored_image[mask]

                # Resize and flip the thermal mask
                resized_thermal = cv2.resize(thermal_mask, (640, 480), interpolation=cv2.INTER_LINEAR)
                flipped_thermal = cv2.flip(resized_thermal, 1)

                # Merge thermal overlay with Pi camera frame
                output_image = cv2.addWeighted(flipped_thermal, 0.5, pi_camera_frame, 0.5, 0)

                # Display the Set, Lower, and Upper limits
                cv2.putText(output_image, f"Set: {temp_threshold}C", (10, 30),
                            cv2.FONT_HERSHEY_DUPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(output_image, f"Lower: {temp_lower_limit}C", (10, 50),
                            cv2.FONT_HERSHEY_DUPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(output_image, f"Upper: {temp_upper_limit}C", (10, 70),
                            cv2.FONT_HERSHEY_DUPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

        # Add the crosshair to the output image
        center_x = output_image.shape[1] // 2
        center_y = output_image.shape[0] // 2
        draw_crosshair(output_image, center_x, center_y, alpha=0.5)

        # Display the center temperature
        center_row = mlx_shape[0] // 2
        center_col = mlx_shape[1] // 2
        center_temp = thermal_array[center_row, center_col]
        cv2.putText(output_image, f"{center_temp:.1f}C", (center_x - 70, center_y - 20),
                    cv2.FONT_HERSHEY_DUPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

        # Display the output
        # Display the output
        cv2.namedWindow("Camera Output", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("Camera Output", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow("Camera Output", output_image)


        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Quit the program
            break
        elif key == ord('a'):  # Cycle display mode
            display_mode = (display_mode + 1) % 4  # Now includes 4 modes
        elif key == 81:  # Left arrow key
            temp_threshold = max(-40, temp_threshold - 1)  # Decrease threshold
        elif key == 83:  # Right arrow key
            temp_threshold = min(300, temp_threshold + 1)  # Increase threshold
        elif key == ord('h'):  # Set upper limit
            temp_upper_limit = min(300, temp_threshold)
        elif key == ord('l'):  # Set lower limit
            temp_lower_limit = max(-40, temp_threshold)

    except Exception as e:
        print(f"Main loop error: {e}")

# Clean up
cv2.destroyAllWindows()
picam2.stop()