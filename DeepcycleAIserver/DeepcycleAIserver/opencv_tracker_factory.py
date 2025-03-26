import cv2

def create_tracker(name="KCF"):
    """
    OpenCV 버전에 따라 트래커 객체 생성
    """
    if hasattr(cv2, 'legacy'):
        tracker_class = getattr(cv2.legacy, f'Tracker{name}_create', None)
    else:
        tracker_class = getattr(cv2, f'Tracker{name}_create', None)

    if tracker_class is None:
        raise AttributeError(f"Tracker {name} is not available in your OpenCV build.")
    
    return tracker_class()
