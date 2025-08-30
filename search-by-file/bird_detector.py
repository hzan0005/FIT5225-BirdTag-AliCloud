# bird_detector.py
from ultralytics import YOLO
import supervision as sv
import cv2 as cv
import numpy as np
from collections import Counter

# IMPORTANT: The model should be loaded only ONCE.
# We define it globally so that Function Compute can reuse it across invocations (on a "warm" instance).
MODEL_PATH = './model.pt' # The model will be in the same directory in the FC environment
model = YOLO(MODEL_PATH)
class_dict = model.names

def detect_birds_in_image(image_bytes):
    """
    Detects birds in an image provided as bytes and returns a count of each species.

    Parameters:
        image_bytes (bytes): The raw byte content of the image file.

    Returns:
        dict: A dictionary with detected bird names as keys and their counts as values.
              Example: {'crow': 2, 'pigeon': 1}
    """
    try:
        # Convert bytes to a NumPy array, then decode it into an image
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv.imdecode(np_arr, cv.IMREAD_COLOR)

        if img is None:
            print("Failed to decode image from bytes.")
            return {}

        # Run the model on the image
        result = model(img)[0]
        detections = sv.Detections.from_ultralytics(result)

        # Filter detections based on a confidence threshold
        confidence_threshold = 0.5
        detections = detections[(detections.confidence > confidence_threshold)]

        if detections.class_id is None or len(detections.class_id) == 0:
            return {}

        # Get the names of detected classes
        detected_class_names = [class_dict[cls_id] for cls_id in detections.class_id]

        # Count the occurrences of each class name
        bird_counts = dict(Counter(detected_class_names))

        print(f"Detection successful. Found: {bird_counts}")
        return bird_counts

    except Exception as e:
        print(f"An error occurred during bird detection: {e}")
        return {}

# Note: The video prediction function is removed for simplicity in this step.
# It can be added back later following a similar refactoring pattern.