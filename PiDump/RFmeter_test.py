import spidev
import time
import logging

# Constants (matching definitions from the C program)
RFMETER_FILTER_USEFULL_DATA = 0x1FFE
RFMETER_ADC_RESOLUTION = 4096
RFMETER_DEF_VREF = 2.5
RFMETER_DEF_SLOPE = -0.025
RFMETER_DEF_INTERCEPT = 20.0
RFMETER_DEF_LIMIT_HIGH = 2.0
RFMETER_DEF_LIMIT_LOW = 0.5

class RfMeter:
    def __init__(self, bus=0, device=0, speed=100000):
        """
        Initialize SPI communication with the ADC.
        :param bus: SPI bus number (usually 0)
        :param device: SPI device number (chip select, usually 0)
        :param speed: SPI clock speed in Hz
        """
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed
        self.spi.mode = 0  # SPI mode 0

    def read_data(self):
        """
        Reads 2 bytes from the ADC over SPI and combines them into a 16-bit integer.
        """
        time.sleep(0.001)  # Small delay before SPI transfer
        # Send two dummy bytes to read 2 bytes from the ADC
        result = self.spi.xfer2([0x00, 0x00])
        time.sleep(0.001)  # Small delay after SPI transfer
        # Combine the two bytes into a 16-bit integer
        data = (result[0] << 8) | result[1]
        return data

    def get_raw_data(self):
        """
        Extract the useful 12-bit ADC reading from the 16-bit data.
        """
        result = self.read_data()
        # Apply bit mask and shift: (result & 0x1FFE) >> 1
        result = (result & RFMETER_FILTER_USEFULL_DATA) >> 1
        return result

    def get_voltage(self):
        """
        Converts the 12-bit ADC reading to a voltage.
        """
        reading = self.get_raw_data()
        voltage = (float(reading) * RFMETER_DEF_VREF) / RFMETER_ADC_RESOLUTION
        return voltage

    def get_signal_strength(self, slope, intercept):
        """
        Converts the measured voltage into RF signal strength (in dBm) using a linear transformation.
        Voltage values outside the defined limits are clamped.
        """
        voltage = self.get_voltage()
        if voltage > RFMETER_DEF_LIMIT_HIGH:
            result = (RFMETER_DEF_LIMIT_HIGH / slope) + intercept
        elif voltage < RFMETER_DEF_LIMIT_LOW:
            result = (RFMETER_DEF_LIMIT_LOW / slope) + intercept
        else:
            result = (voltage / slope) + intercept
        return result

def main():
    # Setup logging (similar to log_init in C)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    logger = logging.getLogger()

    logger.info("---- Application Init ----")

    # Initialize the RF Meter driver using SPI on bus 0, device 0
    try:
        rfmeter = RfMeter(bus=0, device=0, speed=100000)
    except Exception as e:
        logger.error("Failed to initialize SPI: %s", e)
        return

    logger.info("-----------------------")
    logger.info("    RF Meter Click      ")
    logger.info("-----------------------")

    # Main loop: repeatedly measure and log the signal strength
    while True:
        signal_strength = rfmeter.get_signal_strength(RFMETER_DEF_SLOPE, RFMETER_DEF_INTERCEPT)
        logger.info("Signal strength: %.2f dBm", signal_strength)
        time.sleep(0.1)
        logger.info("-----------------------")

if __name__ == '__main__':
    main()