import gpiod
import spidev
import time
import numpy as np
import cv2

import os
os.environ["QT_QPA_PLATFORM"] = "xcb"

# Constants
CHIP = "/dev/gpiochip4"  # GPIO chip for Raspberry Pi 5

# Primary Servo (MG996R) on GPIO 12
PRIMARY_SERVO_PIN = 12
PRIMARY_START_ANGLE = 0
PRIMARY_END_ANGLE = 90

# Micro Servo on GPIO 18
MICRO_SERVO_PIN = 18
MICRO_START_ANGLE = 140  # Start at 140°
MICRO_END_ANGLE = 80  # End at 80°

# Servo timing (50Hz)
PWM_FREQUENCY = 50  # 50Hz
MIN_PULSE_WIDTH = 0.5  # milliseconds (0° position)
MAX_PULSE_WIDTH = 2.5  # milliseconds (180° position)
PERIOD = 20  # milliseconds (1/Frequency = 20ms for 50Hz)

# RF Power Measurement Constants
SPI_BUS = 0
SPI_CS = 0  # Chip Select CE0 (GPIO 8)
SPI_SPEED_HZ = 1600000000  # 1 MHz SPI speed
SPI_MODE = 1  # MCP3201 works in SPI mode 0 or 1
ADC_RESOLUTION = 4095  # 12-bit ADC
V_REF = 2.5  # Reference voltage
DEFAULT_SLOPE = -0.025  # V/dB
DEFAULT_INTERCEPT = 20.0  # dBm

# Setup SPI for RF Power Measurement
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_CS)
spi.max_speed_hz = SPI_SPEED_HZ
spi.mode = SPI_MODE

def read_adc_mcp3201():
    """Read raw 12-bit value from MCP3201 ADC via SPI."""
    bytes_in = spi.xfer2([0x00, 0x00])  # Send dummy bytes to receive data
    raw16 = (bytes_in[0] << 8) | bytes_in[1]
    adc_value = (raw16 >> 3) & 0x0FFF  # Extract the 12-bit ADC result
    return adc_value

def get_rf_power_dbm():
    """Convert ADC raw value to RF power in dBm with increased sensitivity for weak signals."""
    adc_val = read_adc_mcp3201()
    voltage = (adc_val / ADC_RESOLUTION) * V_REF
    idle_adc_val = read_adc_mcp3201()
    idle_voltage = (idle_adc_val / ADC_RESOLUTION) * V_REF
    adjusted_intercept = - (idle_voltage / DEFAULT_SLOPE)
    power_dbm = adjusted_intercept + (voltage / DEFAULT_SLOPE)
    
    # Increase sensitivity further for weak signals
    if power_dbm < -40:
        power_dbm += 8  # Increase sensitivity more aggressively
    elif power_dbm < -30:
        power_dbm += 5  # Moderate boost for weak signals
    
    return power_dbm

# Setup GPIO for Servos
chip = gpiod.Chip(CHIP)
primary_servo = chip.get_line(PRIMARY_SERVO_PIN)
micro_servo = chip.get_line(MICRO_SERVO_PIN)
primary_servo.request(consumer="primary_servo", type=gpiod.LINE_REQ_DIR_OUT)
micro_servo.request(consumer="micro_servo", type=gpiod.LINE_REQ_DIR_OUT)

# Generate software PWM
def set_servo_angle(servo, angle):
    duty_cycle = (MIN_PULSE_WIDTH + (angle / 180.0) * (MAX_PULSE_WIDTH - MIN_PULSE_WIDTH)) / PERIOD * 100
    high_time = (duty_cycle / 100) * PERIOD  # Convert to time in ms
    low_time = PERIOD - high_time  # Remaining time for a full cycle

    for _ in range(25):  # Reduce iterations for faster response
        servo.set_value(1)
        time.sleep(high_time / 1000)  # Convert ms to seconds
        servo.set_value(0)
        time.sleep(low_time / 1000)

# Initialize RF power matrix
rf_data = []

try:
    # Initialize micro servo at 140°
    print(f"Initializing micro servo to {MICRO_START_ANGLE}°...")
    set_servo_angle(micro_servo, MICRO_START_ANGLE)
    time.sleep(0.5)

    micro_angle = MICRO_START_ANGLE  # Start position of micro servo

    while micro_angle >= MICRO_END_ANGLE:
        print(f"Starting new scan cycle. Micro Servo: {micro_angle}°")
        rf_row = []  # Start a new row in the matrix

        print("Moving primary servo from 0° to 90°...")
        for angle in range(PRIMARY_START_ANGLE, PRIMARY_END_ANGLE + 1, 10):
            set_servo_angle(primary_servo, angle)
            rf_power = get_rf_power_dbm()
            print(f"Primary {angle}° | Micro {micro_angle}° | RF Power: {rf_power:.2f} dBm")
            rf_row.append(rf_power)
        
        rf_data.append(rf_row)  # Store the row
        
        print("Moving micro servo down by 10°...")
        micro_angle -= 10
        if micro_angle < MICRO_END_ANGLE:
            break  # Stop movement when reaching 80°
        set_servo_angle(micro_servo, micro_angle)
        
        print("Moving primary servo from 90° to 0°...")
        reverse_rf_row = []
        for angle in range(PRIMARY_END_ANGLE, PRIMARY_START_ANGLE - 1, -10):
            set_servo_angle(primary_servo, angle)
            rf_power = get_rf_power_dbm()
            print(f"Primary {angle}° | Micro {micro_angle}° | RF Power: {rf_power:.2f} dBm")
            reverse_rf_row.append(rf_power)
        
        rf_data.append(reverse_rf_row)  # Store the row

        print("Moving micro servo down by 10° after reverse sweep...")
        micro_angle -= 10
        if micro_angle < MICRO_END_ANGLE:
            break  # Stop movement when reaching 80°
        set_servo_angle(micro_servo, micro_angle)

    print("Servo movement complete. All sweeps completed.")

except KeyboardInterrupt:
    print("Interrupted!")

finally:
    primary_servo.release()
    micro_servo.release()
    spi.close()  # Close SPI connection
