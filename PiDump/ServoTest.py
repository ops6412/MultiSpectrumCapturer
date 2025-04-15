import time
import gpiod

# GPIO pin configuration
servo_pin = 18  # Servo motor connected to GPIO pin 18
relay_pin = 17  # Relay connected to GPIO pin 17

# Open the GPIO chip
chip = gpiod.Chip('gpiochip0')

# Set up the lines for servo and relay
servo_line = chip.get_line(servo_pin)
relay_line = chip.get_line(relay_pin)

# Configure the lines as output
servo_line.request(consumer='servo', type=gpiod.LINE_REQ_DIR_OUT)
relay_line.request(consumer='relay', type=gpiod.LINE_REQ_DIR_OUT)

# Function to turn the servo to a specific angle
def set_servo_angle(angle):
    # Convert angle to duty cycle (MG996R)
    duty = (angle / 18) + 2
    # Move servo to the corresponding position
    servo_line.set_value(1)  # Enable PWM for the servo
    # Simulate the PWM signal by changing the duty cycle (you can implement PWM control manually or use a library)
    time.sleep(duty / 100)  # Simulate PWM duration (you can replace this with actual PWM control)
    servo_line.set_value(0)  # Disable PWM
    time.sleep(1)  # Allow time for the servo to reach the position

# Power on the relay to power the servo
def power_on_servo():
    relay_line.set_value(1)
    time.sleep(1)  # Allow some time for the servo to power on

# Power off the relay to cut the power to the servo
def power_off_servo():
    relay_line.set_value(0)
    time.sleep(1)  # Allow time for the servo to power off

try:
    # Power on the servo
    power_on_servo()
    
    # Move servo to 0 degrees
    set_servo_angle(0)
    time.sleep(2)
    
    # Move servo to 90 degrees
    set_servo_angle(90)
    time.sleep(2)
    
    # Move servo to 180 degrees
    set_servo_angle(180)
    time.sleep(2)

finally:
    # Power off the servo after operation
    power_off_servo()

    # Cleanup GPIO settings (gpiod handles cleanup automatically)
    chip.close()
