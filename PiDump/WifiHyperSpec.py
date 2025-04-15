# Initialize MLX90640 sensor
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
mlx_shape = (24, 32)
frame = [0] * mlx_shape[0] * mlx_shape[1]

# Helper function to align and crop thermal data
def align_and_crop(colored_image, array):
    fov_ratio = 50.0 / 120.0  # Crop from 120-degree FOV to 50-degree FOV
    cropped_width = int(mlx_shape[1] * fov_ratio)
    cropped_height = int(mlx_shape[0] * fov_ratio)
    offset_x = 1  # Adjust horizontal offset
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


i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
mlx_shape = (24, 32)
frame = [0] * mlx_shape[0] * mlx_shape[1]

def capture_thermal_image():
    mlx.getFrame(frame)
    thermal_array = np.array(frame).reshape(mlx_shape)
    normalized_array = ((thermal_array - np.min(thermal_array)) / (np.max(thermal_array) - np.min(thermal_array)) * 255).astype(np.uint8)
    thermal_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)
    thermal_resized = cv2.resize(thermal_image, (width, height), interpolation=cv2.INTER_LINEAR)
    return thermal_resized

height, width = frame0.shape[:2]
thermal_resized = capture_thermal_image()
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
mlx_shape = (24, 32)
frame = [0] * mlx_shape[0] * mlx_shape[1]

mlx.getFrame(frame)
thermal_array = np.array(frame).reshape(mlx_shape)
normalized_array = ((thermal_array - np.min(thermal_array)) / (np.max(thermal_array) - np.min(thermal_array)) * 255).astype(np.uint8)
thermal_image = cv2.applyColorMap(normalized_array, cv2.COLORMAP_JET)
thermal_resized = cv2.resize(thermal_image, (width, height), interpolation=cv2.INTER_LINEAR)

# Initialize Pi Cameras
picam0 = Picamera2(0)
picam1 = Picamera2(1)

# Servo Movement and RF Data Collection
rf_data = []
micro_angle = MICRO_START_ANGLE

try:
    print(f"Initializing micro servo to {MICRO_START_ANGLE}°...")
    set_servo_angle(micro_servo, MICRO_START_ANGLE)
    time.sleep(0.5)
    
    while micro_angle >= MICRO_END_ANGLE:
        print(f"Starting new scan cycle. Micro Servo: {micro_angle}°")
        rf_row = []
        
        print("Moving primary servo from 0° to 120°...")
        for angle in range(PRIMARY_START_ANGLE, PRIMARY_END_ANGLE + 1, 10):
            set_servo_angle(primary_servo, angle)
            rf_power = get_rf_power_dbm()
            rf_row.append(rf_power)
        rf_data.append(rf_row)
        
        print("Moving micro servo down by 5°...")
        micro_angle -= 10
        if micro_angle < MICRO_END_ANGLE:
            break
        set_servo_angle(micro_servo, micro_angle)
    
except KeyboardInterrupt:
    print("Interrupted!")

finally:
    primary_servo.release()
    micro_servo.release()
    spi.close()

# Convert RF Data to an Image
rf_matrix = np.array(rf_data)
picam0.start()
picam1.start()
frame0 = picam0.capture_array()
frame1 = picam1.capture_array()
picam0.stop()
picam1.stop()
frame0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2RGB)
frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
height, width = frame0.shape[:2]
rf_matrix_resized = cv2.resize(rf_matrix, (width, height), interpolation=cv2.INTER_LINEAR)
rf_colormap = cv2.applyColorMap(cv2.convertScaleAbs(rf_matrix_resized, alpha=255/np.max(rf_matrix_resized)), cv2.COLORMAP_JET)

# Initialize visibility and opacity controls
visibility = {'frame0': True, 'frame1': False, 'thermal': False, 'rf': False}
opacity = {'frame0': 1.0, 'frame1': 1.0, 'thermal': 1.0, 'rf': 1.0}

def update_display():
    overlay = np.zeros_like(frame0, dtype=np.float32)
    if visibility['frame0']:
        overlay += (frame0.astype(np.float32) * opacity['frame0'])
    if visibility['frame1']:
        overlay += (frame1.astype(np.float32) * opacity['frame1'])
    if visibility['thermal']:
        overlay += (thermal_resized.astype(np.float32) * opacity['thermal'])
    if visibility['rf']:
        overlay += (rf_colormap.astype(np.float32) * opacity['rf'])
    overlay = np.clip(overlay, 0, 255).astype(np.uint8)
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
    elif key == ord('4'):
        toggle_frame('rf')
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
    elif key == ord('t'):
        adjust_opacity('rf', 0.1)
    elif key == ord('g'):
        adjust_opacity('rf', -0.1)

cv2.destroyAllWindows()
