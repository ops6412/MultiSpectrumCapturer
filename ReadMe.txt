The below install is for manual operation of the library. For the Pip install from PyPi skip the below and simply execute pip3 install pithermalcam.

Install, using apt-get, the following items: libatlas-base-dev python-smbus i2c-tools

Install remaining requirements using either: a. pip3 install the requirements.txt or b. pip3 install the requirements_without_opencv.txt

Download, build, and install OpenCV locally (painstaking process, but results in more optimized code.).

Install cmapy using --no-deps pip3 flag to avoid installing OpenCV via pip3.
