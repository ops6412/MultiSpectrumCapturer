from picamzero import Camera
from time import sleep

cam = Camera()
cam.flip_camera(hflip=True, vflip=True)
cam.start_preview()

sleep(120)