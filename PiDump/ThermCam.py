import board
import busio
import adafruit_mlx90640
import time
import numpy as np
import cv2

# Set up I2C communication
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)

# Initialize MLX90640 sensor
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ  # Set the refresh rate

# Create a buffer for the temperatures
mlx_shape = (24, 32)  # 24 rows and 32 columns
frame = [0] * mlx_shape[0] * mlx_shape[1]  # 768 pixels

# Interpolation toggle (default is nearest neighbor)
use_nearest_neighbor = True

while True:
    try:
        # Read the temperature data
        mlx.getFrame(frame)

        # Convert the temperature values to a NumPy array for image processing
        thermal_array = np.array(frame).reshape(mlx_shape)  # 24x32 array

        # Normalize temperatures to a 0-255 range for mapping to a colormap
        min_temp = np.min(thermal_array)
        max_temp = np.max(thermal_array)
        normalized_array = (thermal_array - min_temp) / (max_temp - min_temp) * 255
        normalized_array = normalized_array.astype(np.uint8)

        # Apply a colormap to create a full gradient
        colored_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)

        # Determine interpolation method based on the toggle
        interpolation = cv2.INTER_NEAREST if use_nearest_neighbor else cv2.INTER_LINEAR

        # Scale up the image using the chosen interpolation method
        scaled_image = cv2.resize(colored_image, (640, 480), interpolation=interpolation)

        # Add text overlay to indicate the current interpolation method
        overlay_text = "Nearest Neighbor" if use_nearest_neighbor else "Bi-linear"
        cv2.putText(scaled_image, f"Interpolation: {overlay_text}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        # Show the image in a window
        cv2.imshow("Thermal Camera Output", scaled_image)

        # Handle keyboard input for toggling interpolation and exiting
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Quit the program
            break
        elif key == ord('a'):  # Toggle interpolation
            use_nearest_neighbor = not use_nearest_neighbor

        # Optional: Add a small delay to avoid overwhelming the terminal
        time.sleep(0.5)

    except Exception as e:
        print(f"Error reading MLX90640 data: {e}")

# Close the OpenCV window
cv2.destroyAllWindows()
