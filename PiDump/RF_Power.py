import spidev
import time

# SPI Configuration
SPI_BUS = 0
SPI_CS = 0  # Chip Select CE0 (GPIO 8)
SPI_SPEED_HZ = 1000000  # 1 MHz SPI speed
SPI_MODE = 1  # MCP3201 works in SPI mode 0 or 1

# ADC & Calibration Constants
ADC_RESOLUTION = 4095  # 12-bit ADC = 2^12 - 1
V_REF = 2.5  # Reference voltage for ADC (typically 2.5V for MCP3201)
DEFAULT_SLOPE = -0.025  # V/dB
DEFAULT_INTERCEPT = 20.0  # dBm

# Initialize SPI
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_CS)
spi.max_speed_hz = SPI_SPEED_HZ
spi.mode = SPI_MODE

def read_adc_mcp3201():
    """Read raw 12-bit value from MCP3201 ADC via SPI."""
    # MCP3201 sends a 12-bit result in two bytes (16 clocks total)
    bytes_in = spi.xfer2([0x00, 0x00])  # Send dummy bytes to receive data
    # Combine bytes into a 16-bit value
    raw16 = (bytes_in[0] << 8) | bytes_in[1]
    # Extract the 12-bit ADC result (ignore leading null bit & padding)
    adc_value = (raw16 >> 3) & 0x0FFF  # Shift right 3 bits & mask 12-bit result
    return adc_value

def get_raw_adc_value():
    """Reads and prints the raw 12-bit ADC value for debugging."""
    adc_val = read_adc_mcp3201()
    print(f"Raw ADC Value: {adc_val}")  # Print the actual ADC reading
    return adc_val


def get_rf_power_dbm():
    """Convert ADC raw value to RF power in dBm."""
    # Step 1: Read ADC
    adc_val = read_adc_mcp3201()
    
    # Step 2: Convert ADC value to voltage
    voltage = (adc_val / ADC_RESOLUTION) * V_REF
    
    # Step 3: Convert voltage to dBm using AD8318 response equation
    power_dbm = DEFAULT_INTERCEPT + (voltage / DEFAULT_SLOPE)
    
    return power_dbm

# Main loop to read RF power
print("Reading RF power in dBm... Press Ctrl+C to stop.")
try:
    while True:
        rf_power = get_rf_power_dbm()
        print(f"Signal Strength: {rf_power:.2f} dBm")
        time.sleep(1)  # 1-second delay
except KeyboardInterrupt:
    spi.close()
    print("SPI connection closed.")



