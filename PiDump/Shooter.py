import gpiod
import spidev
import time
import numpy as np
import cv2
import os

os.environ["QT_QPA_PLATFORM"] = "xcb"

# Constants
CHIP = "/dev/gpiochip4"  # GPIO chip for Raspberry Pi 5

# Servo Pins and Angles
PRIMARY_SERVO_PIN = 12
PRIMARY_START_ANGLE = 0
PRIMARY_END_ANGLE = 120

MICRO_SERVO_PIN = 18
MICRO_START_ANGLE = 160
MICRO_END_ANGLE = 80

# Servo PWM settings
PWM_FREQUENCY = 50
MIN_PULSE_WIDTH = 0.5
MAX_PULSE_WIDTH = 2.5
PERIOD = 20  # ms

# RF Meter Constants
RFMETER_FILTER_USEFULL_DATA = 0x1FFE
RFMETER_ADC_RESOLUTION = 4096
RFMETER_DEF_VREF = 2.5
RFMETER_DEF_SLOPE = -0.025
RFMETER_DEF_INTERCEPT = 20.0
RFMETER_DEF_LIMIT_HIGH = 2.0
RFMETER_DEF_LIMIT_LOW = 0.5

# -------- RF Meter Class --------
class RfMeter:
    def __init__(self, bus=0, device=0, speed=100000):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed
        self.spi.mode = 0

    def read_data(self):
        time.sleep(0.001)
        result = self.spi.xfer2([0x00, 0x00])
        time.sleep(0.001)
        data = (result[0] << 8) | result[1]
        return data

    def get_raw_data(self):
        result = self.read_data()
        return (result & RFMETER_FILTER_USEFULL_DATA) >> 1

    def get_voltage(self):
        reading = self.get_raw_data()
        return (float(reading) * RFMETER_DEF_VREF) / RFMETER_ADC_RESOLUTION

    def get_signal_strength(self, slope, intercept):
        voltage = self.get_voltage()
        if voltage > RFMETER_DEF_LIMIT_HIGH:
            return (RFMETER_DEF_LIMIT_HIGH / slope) + intercept
        elif voltage < RFMETER_DEF_LIMIT_LOW:
            return (RFMETER_DEF_LIMIT_LOW / slope) + intercept
        return (voltage / slope) + intercept

    def close(self):
        self.spi.close()

# Setup GPIO for Servos
chip = gpiod.Chip(CHIP)
primary_servo = chip.get_line(PRIMARY_SERVO_PIN)
micro_servo = chip.get_line(MICRO_SERVO_PIN)
primary_servo.request(consumer="primary_servo", type=gpiod.LINE_REQ_DIR_OUT)
micro_servo.request(consumer="micro_servo", type=gpiod.LINE_REQ_DIR_OUT)

# Servo PWM function
def set_servo_angle(servo, angle):
    duty_cycle = (MIN_PULSE_WIDTH + (angle / 180.0) * (MAX_PULSE_WIDTH - MIN_PULSE_WIDTH)) / PERIOD * 100
    high_time = (duty_cycle / 100) * PERIOD
    low_time = PERIOD - high_time
    for _ in range(25):
        servo.set_value(1)
        time.sleep(high_time / 1000)
        servo.set_value(0)
        time.sleep(low_time / 1000)

# Initialize RF meter
rfmeter = RfMeter()

# Initialize RF data matrix
rf_data = []

try:
    print(f"Initializing micro servo to {MICRO_START_ANGLE}°...")
    set_servo_angle(micro_servo, MICRO_START_ANGLE)
    time.sleep(0.5)

    micro_angle = MICRO_START_ANGLE

    while micro_angle >= MICRO_END_ANGLE:
        print(f"Starting new scan cycle. Micro Servo: {micro_angle}°")
        rf_row = []

        print("Moving primary servo from 0° to 120°...")
        for angle in range(PRIMARY_START_ANGLE, PRIMARY_END_ANGLE + 1, 10):
            set_servo_angle(primary_servo, angle)
            rf_power = rfmeter.get_signal_strength(RFMETER_DEF_SLOPE, RFMETER_DEF_INTERCEPT)
            print(f"Primary {angle}° | Micro {micro_angle}° | RF Power: {rf_power:.2f} dBm")
            rf_row.append(rf_power)
        
        rf_data.append(rf_row)

        micro_angle -= 5
        if micro_angle < MICRO_END_ANGLE:
            break
        set_servo_angle(micro_servo, micro_angle)

        print("Moving primary servo from 120° to 0°...")
        reverse_rf_row = []
        for angle in range(PRIMARY_END_ANGLE, PRIMARY_START_ANGLE - 1, -10):
            set_servo_angle(primary_servo, angle)
            rf_power = rfmeter.get_signal_strength(RFMETER_DEF_SLOPE, RFMETER_DEF_INTERCEPT)
            print(f"Primary {angle}° | Micro {micro_angle}° | RF Power: {rf_power:.2f} dBm")
            reverse_rf_row.append(rf_power)
        
        rf_data.append(reverse_rf_row)

        micro_angle -= 5
        if micro_angle < MICRO_END_ANGLE:
            break
        set_servo_angle(micro_servo, micro_angle)

    print("Servo movement complete. All sweeps completed.")

except KeyboardInterrupt:
    print("Interrupted!")

finally:
    primary_servo.release()
    micro_servo.release()
    rfmeter.close()

    rf_matrix = np.array(rf_data)
    min_val, max_val = 0, -60
    rf_matrix_normalized = np.clip((rf_matrix - min_val) / (max_val - min_val), 0, 1) * 255
    rf_matrix_uint8 = rf_matrix_normalized.astype(np.uint8)
    rf_colormap = cv2.applyColorMap(255 - rf_matrix_uint8, cv2.COLORMAP_JET)
    rf_colormap_resized = cv2.resize(rf_colormap, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    cv2.imshow("RF Power Heatmap", rf_colormap_resized)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
