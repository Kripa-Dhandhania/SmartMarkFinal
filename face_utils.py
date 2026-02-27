import cv2
import os
import numpy as np

DATASET_DIR = "datasets"
FACE_SIZE = (200, 200)

def capture_face():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[CAMERA] Cannot open camera")
        return None

    print("📷 Camera opened (Press C to capture, Q to quit)")

    face = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Capture Face", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            face = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face = cv2.resize(face, FACE_SIZE)
            break
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return face


def save_face(student_id, face):
    try:
        student_dir = os.path.join(DATASET_DIR, student_id)
        os.makedirs(student_dir, exist_ok=True)
        path = os.path.join(student_dir, "face.jpg")
        cv2.imwrite(path, face)
        print(f"[FACE] Saved at {path}")
        return True
    except Exception as e:
        print("[FACE ERROR]", e)
        return False


def train_recognizer():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = []
    labels = []
    label_map = {}

    label = 0
    if not os.path.exists(DATASET_DIR):
        print("[FACE] Dataset folder missing")
        return recognizer, label_map

    for student_id in os.listdir(DATASET_DIR):
        img_path = os.path.join(DATASET_DIR, student_id, "face.jpg")
        if os.path.exists(img_path):
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            faces.append(img)
            labels.append(label)
            label_map[label] = student_id
            label += 1

    if faces:
        recognizer.train(faces, np.array(labels))
        print("✅ Face recognizer trained")
    else:
        print("[FACE] No face images found in database.")

    return recognizer, label_map


def recognize_face(recognizer, label_map):
    face = capture_face()
    if face is None or not label_map:
        return None

    label, confidence = recognizer.predict(face)
    print(f"[FACE] Confidence: {confidence}")

    if confidence < 80:
        return label_map[label]
    return None
