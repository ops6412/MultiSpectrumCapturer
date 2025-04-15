from gpiozero import Button
from time import sleep

# Setup GPIO pins for three buttons
button1 = Button(22)
button2 = Button(27)
button3 = Button(17)

# Shared variables
set_value = 0
mode = 0
upper = None
lower = None

# Function to record state of a button over 500ms with 100ms intervals
def record_button_state(button):
    high_count = 0
    for i in range(5):
        if button.is_pressed:
            high_count += 1
        sleep(0.1)  # 100ms delay between checks
    return high_count

# Function to handle button states and shared variables
def handle_button_state(button, button_name, add_or_subtract):
    global set_value, mode
    
    high_count = record_button_state(button)
    low_count = 5 - high_count

    if low_count >= 3:
        if add_or_subtract == "add":
            set_value += low_count
        elif add_or_subtract == "subtract":
            set_value -= low_count
        
        # Ensure set_value loops between -40 and 300
        if set_value > 300:
            set_value = -40 + (set_value - 301)
        elif set_value < -40:
            set_value = 300 - (-41 - set_value)
        
        print(f"{button_name} was held, LOW readings: {low_count}")
        print(f"Shared Set: {set_value}")
    elif 0 < low_count < 3:
        if add_or_subtract == "add":
            mode += 1
        elif add_or_subtract == "subtract":
            mode -= 1
        if mode > 3:
            mode = 0
        elif mode < 0:
            mode = 3
        print(f"{button_name} was pressed, LOW readings: {low_count}")
        print(f"Shared Mode: {mode}")
    else:
        print(f"{button_name} was not pressed")

# Function to handle the third button for "upper" and "lower"
def handle_third_button(button):
    global upper, lower, set_value