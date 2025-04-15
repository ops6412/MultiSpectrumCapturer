import board
import busio
import adafruit_mlx90640
import numpy as np
import cv2
from picamera2 import Picamera2
import threading
from gpiozero import Button
from time import sleep

# Set up I2C communication for MLX90640
i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)

# Initialize MLX90640 sensor
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_8_HZ

# Create a buffer for the temperatures
mlx_shape = (24, 32)
frame = [0] * mlx_shape[0] * mlx_shape[1]

# Initialize the Raspberry Pi camera with 60 FPS
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"}, controls={"FrameRate": 60})
picam2.configure(preview_config)
picam2.start()

# GPIO button setup
button1 = Button(22)
button2 = Button(27)
button3 = Button(17)

# Shared variables
thermal_image = np.zeros((480, 640, 3), dtype=np.uint8)
thermal_array = np.zeros(mlx_shape)
lock = threading.Lock()
display_mode = 0
temp_threshold = -40
temp_upper_limit = 60
temp_lower_limit = 30
mode_names = ["Normal", "Thermal", "Fade", "Limit"]

# Helper function to align and crop thermal data
def align_and_crop(colored_image, array):
    fov_ratio = 50.0 / 150.0
    cropped_width = int(mlx_shape[1] * fov_ratio)
    cropped_height = int(mlx_shape[0] * fov_ratio)
    offset_x = -1
    center_x = mlx_shape[1] // 2 + offset_x
    center_y = mlx_shape[0] // 2
    start_x = max(center_x - cropped_width // 2, 0)
    start_y = max(center_y - cropped_height // 2, 0)
    end_x = min(center_x + cropped_width // 2, mlx_shape[1])
    end_y = min(center_y + cropped_height // 2, mlx_shape[0])

    cropped_image = colored_image[start_y:end_y, start_x:end_x]
    flipped_image = cv2.flip(cropped_image, 1)
    resized_image = cv2.resize(flipped_image, (640, 480), interpolation=cv2.INTER_LINEAR)

    cropped_array = array[start_y:end_y, start_x:end_x]
    flipped_array = np.flip(cropped_array, axis=1)
    resized_array = cv2.resize(flipped_array, (640, 480), interpolation=cv2.INTER_LINEAR)

    return resized_image, resized_array

# Helper function to draw a crosshair and temperature at the center
def draw_crosshair_with_temp(image, center_x, center_y, temp, gap=10, size=20, color=(0, 255, 255), thickness=2, alpha=1.0):
    """
    Draws a crosshair at the center of the image and displays the temperature value.
    
    Parameters:
    - image: The image on which to draw the crosshair.
    - center_x, center_y: The center coordinates for the crosshair.
    - temp: The temperature value to display near the crosshair.
    - gap: The gap between the center and the crosshair lines.
    - size: The length of the crosshair lines.
    - color: The color of the crosshair lines (default: yellow).
    - thickness: The thickness of the crosshair lines.
    - alpha: Transparency of the crosshair overlay (1.0 for solid).
    """
    overlay = image.copy()

    # Draw horizontal lines
    cv2.line(overlay, (center_x - size, center_y), (center_x - gap, center_y), color, thickness)
    cv2.line(overlay, (center_x + gap, center_y), (center_x + size, center_y), color, thickness)

    # Draw vertical lines
    cv2.line(overlay, (center_x, center_y - size), (center_x, center_y - gap), color, thickness)
    cv2.line(overlay, (center_x, center_y + gap), (center_x, center_y + size), color, thickness)

    # Blend the overlay with the main image
    cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

    # Display temperature value near the crosshair
    draw_text(image, f"{temp:.1f}C", (center_x + 10, center_y - 10), font_scale=1.0, color=color, thickness=2)


# Helper function to draw text consistently
def draw_text(image, text, position, font=cv2.FONT_HERSHEY_PLAIN, font_scale=1, color=(255, 255, 255), thickness=1):
    cv2.putText(image, text, position, font, font_scale, color, thickness, cv2.LINE_AA)

# Thermal processing thread
def process_thermal():
    global thermal_image, thermal_array
    while True:
        try:
            mlx.getFrame(frame)
            thermal_array = np.array(frame).reshape(mlx_shape)
            min_temp = np.min(thermal_array)
            max_temp = np.max(thermal_array)
            normalized_array = ((thermal_array - min_temp) / (max_temp - min_temp) * 255).astype(np.uint8)
            colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)
            aligned_image, _ = align_and_crop(colored_image, thermal_array)
            with lock:
                thermal_image = aligned_image
        except Exception as e:
            print(f"Thermal processing error: {e}")

thermal_thread = threading.Thread(target=process_thermal, daemon=True)
thermal_thread.start()

# Function to sample button state over 300ms
def sample_button(button):
    high_count = 0
    for _ in range(6):  # Sample 6 times over 300ms
        if button.is_pressed:
            high_count += 1
        sleep(0.05)  # 50ms interval
    return high_count

# Button handling threads
def handle_button1():
    global temp_threshold, display_mode
    while True:
        if button1.is_pressed:
            high_count = sample_button(button1)
            low_count = 6 - high_count
            if low_count >= 3:  # Held (long press)
                temp_threshold += 10
                temp_threshold = min(300, max(-40, temp_threshold))
                print(f"Set value increased to: {temp_threshold}")
            elif 0 < low_count < 3:  # Pressed (short press)
                display_mode = (display_mode + 1) % 4
                print(f"Mode switched to: {mode_names[display_mode]}")
        sleep(0.1)

def handle_button2():
    global temp_threshold, display_mode
    while True:
        if button2.is_pressed:
            high_count = sample_button(button2)
            low_count = 6 - high_count
            if low_count >= 3:  # Held (long press)
                temp_threshold -= 10
                temp_threshold = min(300, max(-40, temp_threshold))
                print(f"Set value decreased to: {temp_threshold}")
            elif 0 < low_count < 3:  # Pressed (short press)
                display_mode = (display_mode - 1) % 4
                print(f"Mode switched to: {mode_names[display_mode]}")
        sleep(0.1)

def handle_button3():
    global temp_upper_limit, temp_lower_limit
    while True:
        if button3.is_pressed:
            high_count = sample_button(button3)
            if high_count >= 3:  # Held (long press)
                temp_lower_limit = temp_threshold
                print(f"Lower limit set to: {temp_lower_limit}")
            elif 0 < high_count < 3:  # Pressed (short press)
                temp_upper_limit = temp_threshold
                print(f"Upper limit set to: {temp_upper_limit}")
        sleep(0.1)

# Start button handling threads
threading.Thread(target=handle_button1, daemon=True).start()
threading.Thread(target=handle_button2, daemon=True).start()
threading.Thread(target=handle_button3, daemon=True).start()

# OpenCV window setup
cv2.namedWindow("Camera Output", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Camera Output", 640, 480)

# Main loop
try:
    while True:
        pi_camera_frame = picam2.capture_array()
        pi_camera_frame = cv2.cvtColor(pi_camera_frame, cv2.COLOR_BGR2RGB)

        with lock:
            center_row = mlx_shape[0] // 2
            center_col = mlx_shape[1] // 2
            center_temp = thermal_array[center_row, center_col]

        if display_mode == 0:
            output_image = pi_camera_frame
        elif display_mode == 1:
            output_image = thermal_image
        elif display_mode == 2:  # Fade Mode
            mask = thermal_array > temp_threshold
            normalized_array = ((thermal_array - np.min(thermal_array)) / (np.max(thermal_array) - np.min(thermal_array)) * 255).astype(np.uint8)
            colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)
            aligned_image, aligned_array = align_and_crop(colored_image, thermal_array)
            thermal_mask = np.zeros_like(aligned_image)
            thermal_mask[aligned_array > temp_threshold] = aligned_image[aligned_array > temp_threshold]
            output_image = cv2.addWeighted(thermal_mask, 0.5, pi_camera_frame, 0.5, 0)
        elif display_mode == 3:  # Limit Mode
            normalized_array = ((thermal_array - np.min(thermal_array)) / (np.max(thermal_array) - np.min(thermal_array)) * 255).astype(np.uint8)
            colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)
            aligned_image, aligned_array = align_and_crop(colored_image, thermal_array)
            thermal_mask = np.zeros_like(aligned_image)
            mask = (aligned_array >= temp_lower_limit) & (aligned_array <= temp_upper_limit)
            thermal_mask[mask] = aligned_image[mask]
            output_image = cv2.addWeighted(thermal_mask, 0.5, pi_camera_frame, 0.5, 0)

        center_x = output_image.shape[1] // 2
        center_y = output_image.shape[0] // 2
        draw_crosshair_with_temp(output_image, center_x, center_y, center_temp)
        draw_text(output_image, f"Set: {temp_threshold}C", (10, 20))
        draw_text(output_image, mode_names[display_mode], (500, 20))
        if display_mode == 3:
            draw_text(output_image, f"Lower: {temp_lower_limit}C", (10, 40))
            draw_text(output_image, f"Upper: {temp_upper_limit}C", (10, 60))

        cv2.imshow("Camera Output", output_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
except KeyboardInterrupt:
    print("Exiting...")
    cv2.destroyAllWindows()
    picam2.stop()
