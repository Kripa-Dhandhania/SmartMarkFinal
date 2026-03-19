"""
Face Recognition Module for Smart Attendance System
Handles face capture, training, and recognition using LBPH algorithm.
Face images are stored in SQLite database as BLOB.
"""

import cv2
import numpy as np
import os
import time
from pathlib import Path

# Import database functions for face storage (kept for metadata if needed)
from database import (
    save_face_to_db, 
    get_face_from_db, 
    check_face_exists_in_db, 
    get_all_faces_from_db
)

CONFIDENCE_THRESHOLD = 85  # Adjusted from 75 to improve recognition reliability
# Use absolute path for dataset directory to avoid issues with different working directories
DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")


def get_face_cascade():
    """Load Haar cascade for face detection."""
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    return cv2.CascadeClassifier(cascade_path)


def encode_face_to_bytes(face_image):
    """Convert face image (numpy array) to bytes for database storage."""
    success, encoded = cv2.imencode('.jpg', face_image)
    if success:
        return encoded.tobytes()
    return None


def decode_bytes_to_face(face_bytes):
    """Convert bytes from database back to face image (numpy array)."""
    nparr = np.frombuffer(face_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    return image


def check_face_enrolled(student_id):
    """Check if a face image exists for the given student in datasets folder."""
    student_dir = os.path.join(DATASET_DIR, str(student_id))
    if os.path.exists(student_dir):
        # Check if there are any image files in the directory
        images = [f for f in os.listdir(student_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        if len(images) > 0:
            return True
            
    # Fallback to database check for old records
    return check_face_exists_in_db(student_id)


def train_recognizer():
    """
    Train LBPH face recognizer with all faces from datasets folder and database.
    
    Returns:
        Trained recognizer and label-to-student_id mapping, or (None, None) if no data
    """
    faces = []
    labels = []
    label_map = {}  # Maps numeric label to student_id
    current_label = 0
    
    # 1. Load faces from datasets folder (New Storage)
    if not os.path.exists(DATASET_DIR):
        os.makedirs(DATASET_DIR)
        
    for student_id in os.listdir(DATASET_DIR):
        student_dir = os.path.join(DATASET_DIR, student_id)
        if not os.path.isdir(student_dir):
            continue
            
        student_images = [f for f in os.listdir(student_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        
        for img_name in student_images:
            img_path = os.path.join(student_dir, img_name)
            face_image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            
            if face_image is None:
                print(f"[FACE] Warning: Could not read image {img_path}")
                continue
                
            # Resize to standard size
            face_image = cv2.resize(face_image, (200, 200))
            
            # Apply Histogram Equalization to normalize lighting
            face_image = cv2.equalizeHist(face_image)
            
            faces.append(face_image)
            labels.append(current_label)
            label_map[current_label] = student_id
            
            print(f"[FACE] Loaded face from disk for student: {student_id}")
            
        if student_images:
            current_label += 1
    
    # 2. Load faces from database (Legacy Storage)
    all_faces = get_all_faces_from_db()
    for student_id, face_bytes in all_faces:
        # Check if we already loaded this student from disk to avoid duplicate labels
        # (Though LBPH handles multiple images per label well)
        
        face_image = decode_bytes_to_face(face_bytes)
        if face_image is None:
            continue
            
        face_image = cv2.resize(face_image, (200, 200))
        
        # Apply Histogram Equalization to normalize lighting
        face_image = cv2.equalizeHist(face_image)
        
        # We'll assign a new label if this student isn't in label_map already
        # In LBPH, multiple images for the same student SHOULD have the same label
        
        # Find existing label for this student_id
        student_label = None
        for l, s_id in label_map.items():
            if s_id == student_id:
                student_label = l
                break
        
        if student_label is None:
            student_label = current_label
            label_map[student_label] = student_id
            current_label += 1
            
        faces.append(face_image)
        labels.append(student_label)
        print(f"[FACE] Loaded face from database for student: {student_id}")
    
    if len(faces) == 0:
        print("[FACE] No face images found in database or datasets folder.")
        return None, None
    
    # Create and train LBPH recognizer
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    
    print(f"[FACE] Recognizer trained with {len(faces)} face(s).")
    return recognizer, label_map


def capture_face():
    """
    Open webcam and capture a face image with a simple liveness check.
    Asks the user to blink or move to ensure it's not a static photo.
    
    Returns:
        Captured grayscale face image, or None if cancelled/failed
    """
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("[FACE] Error: Could not open camera.")
        return None
    
    face_cascade = get_face_cascade()
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    captured_face = None
    liveness_detected = False
    start_time = time.time()
    
    print("[FACE] Camera opened. Liveness check: Please BLINK or MOVE your head.")
    
    prev_gray = None
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
        
        # Display instructions
        cv2.putText(frame, "Liveness Check: Please BLINK or MOVE", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            roi_gray = gray[y:y+h, x:x+w]
            
            # Simple Liveness 1: Eye Detection
            eyes = eye_cascade.detectMultiScale(roi_gray, 1.1, 10)
            
            # Simple Liveness 2: Movement Detection (Optical Flow / Frame Diff)
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                movement = np.sum(diff) / (gray.shape[0] * gray.shape[1])
                if movement > 2.0: # Threshold for significant movement
                    liveness_detected = True
            
            prev_gray = gray.copy()
            
            if liveness_detected:
                cv2.putText(frame, "Liveness Verified! Press 'C' to Capture", 
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Checking for movement...", 
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.imshow('Attendance - Face Capture', frame)
        key = cv2.waitKey(1) & 0xFF
        
        if (key == ord('c') or key == ord('C')) and liveness_detected:
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                captured_face = gray[y:y+h, x:x+w]
                captured_face = cv2.resize(captured_face, (200, 200))
                captured_face = cv2.equalizeHist(captured_face)
                break
        elif key == ord('q') or key == ord('Q'):
            break
            
        if time.time() - start_time > 30: # Timeout
            print("[FACE] Liveness check timed out.")
            break
    
    cap.release()
    cv2.destroyAllWindows()
    return captured_face


def recognize_face(recognizer, label_map, face_image):
    """
    Recognize a face using the trained recognizer.
    
    Args:
        recognizer: Trained LBPH recognizer
        label_map: Dictionary mapping labels to student IDs
        face_image: Grayscale face image to recognize
    
    Returns:
        (student_id, confidence) if recognized, (None, confidence) otherwise
    """
    if recognizer is None or face_image is None:
        return None, float('inf')
    
    # Apply Histogram Equalization to input image
    face_image = cv2.equalizeHist(face_image)
    
    # Predict
    label, confidence = recognizer.predict(face_image)
    
    predicted_student = label_map.get(label, "Unknown")
    print(f"[FACE] Recognition result - Predicted: {predicted_student}, Confidence: {confidence:.2f}")
    
    # Check if confidence is acceptable (lower is better for LBPH)
    if confidence < CONFIDENCE_THRESHOLD:
        student_id = label_map.get(label)
        print(f"[FACE] Face matched to student: {student_id}")
        return student_id, confidence
    else:
        print(f"[FACE] Face not recognized (confidence {confidence:.2f} > threshold {CONFIDENCE_THRESHOLD})")
        return None, confidence


def save_face(student_id, face_image):
    """
    Save a face image to the datasets folder and optionally database.
    
    Args:
        student_id: Student's unique ID
        face_image: Grayscale face image (numpy array)
    
    Returns:
        True if successful, False otherwise
    """
    if face_image is None:
        print("[FACE] Error: No face image to save.")
        return False
    
    # 1. Save to datasets folder
    try:
        student_dir = os.path.join(DATASET_DIR, str(student_id))
        if not os.path.exists(student_dir):
            os.makedirs(student_dir)
        
        # Limit to 10 images: if more than 10, delete the oldest one
        existing_images = sorted([f for f in os.listdir(student_dir) if f.endswith(('.jpg', '.png', '.jpeg'))])
        if len(existing_images) >= 10:
            try:
                os.remove(os.path.join(student_dir, existing_images[0]))
            except: pass
            
        timestamp = int(time.time() * 1000) # milliseconds for uniqueness
        img_path = os.path.join(student_dir, f"{timestamp}.jpg")
        
        cv2.imwrite(img_path, face_image)
        print(f"[FACE] Saved enrollment image {len(existing_images)+1}/10 for student {student_id}")
    except Exception as e:
        print(f"[FACE] Error saving to disk: {e}")
    
    # 2. Save to database (Legacy support / backup)
    face_bytes = encode_face_to_bytes(face_image)
    if face_bytes:
        save_face_to_db(student_id, face_bytes)
        
    return True


# Test the module
if __name__ == '__main__':
    print("Testing face capture...")
    face = capture_face()
    if face is not None:
        print(f"Face captured! Shape: {face.shape}")
    else:
        print("No face captured.")
