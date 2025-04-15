import spidev
import time

# SPI Configuration
SPI_BUS = 0
SPI_CS = 0  # Use SPI's hardware CS0 (GPIO 8)
SPI_SPEED_HZ = 500000  # 1 MHz SPI speed
SPI_MODE = 1  # MCP3201 works in SPI mode 0 or 1

# ADC & Calibration Constants
ADC_RESOLUTION = 4095  # 12-bit ADC = 2^12 - 1
V_REF = 2.5  # Reference voltage for ADC (typically 2.5V for MCP3201)
DEFAULT_SLOPE = -0.025  # V/dB
DEFAULT_INTERCEPT = 20.0  # dBm

# Initialize SPI (LET IT CONTROL CS)
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_CS)  # Open SPI using CS0 (GPIO 8)
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
    print(f"Raw ADC Value: {adc_val}")  # Debugging output
    
    voltage = (adc_val / ADC_RESOLUTION) * V_REF
    print(f"ADC Voltage: {voltage:.3f}V")  # Debug output
    
    idle_adc_val = read_adc_mcp3201()  # Take another ADC reading as idle reference
    idle_voltage = (idle_adc_val / ADC_RESOLUTION) * V_REF
    print(f"Idle ADC Value: {idle_adc_val}, Idle Voltage: {idle_voltage:.3f}V")
    
    adjusted_intercept = - (idle_voltage / DEFAULT_SLOPE)  # Should output ~0 dBm when idle
    power_dbm = adjusted_intercept + (voltage / DEFAULT_SLOPE)

    # Increase sensitivity further for weak signals
    if power_dbm < -40:  
        power_dbm += 8  # Increase sensitivity more aggressively
    elif power_dbm < -30:
        power_dbm += 5  # Moderate boost for weak signals
    
    print(f"Calculated RF Power: {power_dbm:.2f} dBm")  # Debug output
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


 