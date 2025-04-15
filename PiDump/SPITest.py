import spidev
import time
import os

# SPI Configuration
SPI_BUS = 0
SPI_DEVICE = 0  # CE0 (GPIO 8)
SPI_SPEED_HZ = 10000  # Slow speed for testing
SPI_MODE = 1  # MCP3201 supports SPI Mode 0 or 1

# Initialize SPI
spi = spidev.SpiDev()

def check_spi_enabled():
    """ Check if SPI is enabled on Raspberry Pi. """
    print("\n=== SPI Connection Test ===")
    if os.path.exists("/dev/spidev0.0"):
        print("[✔] SPI device detected: /dev/spidev0.0")
    else:
        print("[✘] SPI device NOT detected! Enable SPI via raspi-config.")
        print("Run: sudo raspi-config -> Interfacing Options -> SPI -> Enable")
        return False
    return True

def test_spi_communication():
    """ Send a test byte over SPI and check if it returns a response. """
    print("\n=== SPI Communication Test ===")
    try:
        spi.open(SPI_BUS, SPI_DEVICE)
        spi.max_speed_hz = SPI_SPEED_HZ
        spi.mode = SPI_MODE

        print("[DEBUG] Sending SPI test command...")
        response = spi.xfer2([0xAA])  # Send test byte (0xAA = 10101010)

        print(f"SPI Response: {response}")  # Should print a response (e.g., [0])
        
        if response == [0]:  # Expected for an SPI read test without a loopback
            print("[✔] SPI bus is active and responding.")
        else:
            print("[⚠] Unexpected SPI response - Check wiring.")

    except Exception as e:
        print(f"[✘] SPI Communication Failed: {e}")

    finally:
        spi.close()

def test_mcp3201_adc():
    """ Read raw 12-bit data from MCP3201 ADC. """
    print("\n=== MCP3201 ADC Read Test ===")
    try:
        spi.open(SPI_BUS, SPI_DEVICE)
        spi.max_speed_hz = SPI_SPEED_HZ
        spi.mode = SPI_MODE

        for _ in range(5):  # Read ADC 5 times for consistency
            print("[DEBUG] Attempting SPI read...")  # Debug before xfer2
            
            response = spi.xfer2([0x00, 0x00])  # Read two bytes from ADC
            
            print(f"SPI Raw Response: {response}")  # Print raw byte response
            
            raw_value = ((response[0] << 8) | response[1]) >> 3  # Extract 12-bit value
            print(f"Raw ADC Value: {raw_value}")

            if raw_value == 0:
                print("[⚠] Warning: ADC output stuck at 0 - Check AD8318 power & input!")
            elif raw_value == 4095:
                print("[⚠] Warning: ADC output stuck at max (4095) - Check AD8318 output!")

            time.sleep(1)

    except Exception as e:
        print(f"[✘] MCP3201 ADC Read error: {e}")

    finally:
        print("[DEBUG] Closing SPI connection...")
        spi.close()

# Run all tests
if __name__ == "__main__":
    if check_spi_enabled():
        test_spi_communication()
        test_mcp3201_adc()

