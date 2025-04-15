from picamera2 import Picamera2
import cv2
import numpy as np

# Initialize both cameras
picam0 = Picamera2(0)  # Camera on Port 0
picam1 = Picamera2(1)  # Camera on Port 1

# Configure cameras
config0 = picam0.create_preview_configuration()
config1 = picam1.create_preview_configuration()

picam0.configure(config0)
picam1.configure(config1)

# Start both cameras
picam0.start()
picam1.start()

# Open a preview window
while True:
    # Capture frames from both cameras
    frame0 = picam0.capture_array()
    frame1 = picam1.capture_array()

    # Fix color mapping (convert BGR to RGB)
    frame0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2RGB)
    frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)

    # Rotate Camera 1 frame 90 degrees clockwise
    frame1 = cv2.rotate(frame1, cv2.ROTATE_90_CLOCKWISE)

    # Resize frames to match height
    height = min(frame0.shape[0], frame1.shape[0])
    frame0 = cv2.resize(frame0, (frame0.shape[1], height))
    frame1 = cv2.resize(frame1, (frame1.shape[1], height))

    # Combine frames horizontally
    combined_frame = np.hstack((frame0, frame1))

    # Display the corrected frame
    cv2.imshow("Dual Camera Stream (Fixed Colors & Rotated Cam1)", combined_frame)

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cv2.destroyAllWindows()
picam0.close()
picam1.close()


