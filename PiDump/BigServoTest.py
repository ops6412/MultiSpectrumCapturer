import gpiod
import time

# Constants
PWM_PIN = 12  # Updated to use GPIO 12
CHIP = "/dev/gpiochip4"  # GPIO chip for Raspberry Pi 5
PWM_FREQUENCY = 50  # 50Hz for servo control

# Servo pulse width range (MG996R typical)
MIN_PULSE_WIDTH = 0.5  # milliseconds (0° position)
MAX_PULSE_WIDTH = 2.5  # milliseconds (180° position)
PERIOD = 20  # milliseconds (1/Frequency = 20ms for 50Hz)

# Calculate duty cycles
def angle_to_duty_cycle(angle):
    pulse_width = MIN_PULSE_WIDTH + (angle / 180.0) * (MAX_PULSE_WIDTH - MIN_PULSE_WIDTH)
    duty_cycle = (pulse_width / PERIOD) * 100  # Convert to percentage
    return duty_cycle

# Setup GPIO
chip = gpiod.Chip(CHIP)
line = chip.get_line(PWM_PIN)
line.request(consumer="servo", type=gpiod.LINE_REQ_DIR_OUT)

# Generate software PWM
def set_servo_angle(angle):
    duty_cycle = angle_to_duty_cycle(angle)
    high_time = (duty_cycle / 100) * PERIOD  # Convert to time in ms
    low_time = PERIOD - high_time  # Remaining time for a full cycle
    
    # Generate PWM pulses manually
    for _ in range(50):  # Run for approximately 1 second
        line.set_value(1)
        time.sleep(high_time / 1000)  # Convert ms to seconds
        line.set_value(0)
        time.sleep(low_time / 1000)

try:
    print("Moving servo from 0° to 90°...")
    for angle in range(0, 91, 10):  # Smooth transition in 10° steps
        set_servo_angle(angle)
        time.sleep(0.5)

    print("Servo movement complete.")

except KeyboardInterrupt:
    print("Interrupted!")

finally:
    line.release()

