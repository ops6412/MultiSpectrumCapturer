import RPi.GPIO as GPIO
import time

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)

# Define the GPIO pin connected to the analog signal
analog_pin = 18  # GPIO18 (Physical pin 12)

# Set up the GPIO pin as an input
GPIO.setup(analog_pin, GPIO.IN)

# Function to measure the time the pin stays HIGH
def measure_high_time():
    start_time = time.time()
    while GPIO.input(analog_pin) == GPIO.LOW:
        start_time = time.time()  # Wait for HIGH transition

    # Measure how long the signal stays HIGH
    while GPIO.input(analog_pin) == GPIO.HIGH:
        pulse_duration = time.time() - start_time

    return pulse_duration

# Main loop to continuously read the HIGH pulse duration
try:
    while True:
        pulse_width = measure_high_time()  # Measure time the signal stays HIGH
        print(f"Pulse Width: {pulse_width:.6f} seconds")
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting...")

finally:
    GPIO.cleanup()
