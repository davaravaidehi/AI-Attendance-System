import dlib
import cv2
import numpy as np
import face_recognition_models
from sklearn.svm import SVC
import streamlit as st


from src.database.db import get_all_students


@st.cache_resource
def load_dlib_models():
    detector = dlib.get_frontal_face_detector()

    sp = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )

    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )

    return detector,sp,facerec


def get_face_embeddings(image_np):

    detector, sp, facerec = load_dlib_models()

    height, width = image_np.shape[:2]

    # Only downscale genuinely huge images — your old code shrank
    # ANY image over 800px wide, which can make a third/side face
    # too small for the detector to find in a group photo.
    max_width = 1600
    if width > max_width:
        scale = max_width / width
        image_np = cv2.resize(image_np, None, fx=scale, fy=scale)

    # Try harder before giving up: upsampling helps find smaller/
    # angled faces, at the cost of speed. Stop as soon as we find some.
    faces = []
    for upsample in (1, 2, 3):
        faces = detector(image_np, upsample)
        print(f"[detector] upsample={upsample} -> faces found: {len(faces)}")
        if len(faces) >= 1:
            break

    encodings = []

    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 1)
        encodings.append(np.array(face_descriptor))

    return encodings


@st.cache_resource
def get_trained_model():
    x = []
    y = []
    student_db = get_all_students()

    if not student_db:
        return None
    for student in student_db:
        embedding = student.get("face_embedding")
        if embedding:
            x.append(np.array(embedding))
            y.append(student.get('student_id'))

    if len(x) == 0:
        return 0
    clf = SVC(kernel='linear', probability=True,class_weight='balanced')

    try:
        clf.fit(x,y)
    except ValueError:
        pass

    return {'clf':clf,'x':x,'y':y}


def train_classifire():
    st.cache_resource.clear()
    model_data = get_trained_model()
    return bool(model_data)


def predict_attendance(class_image_np):
    """
    Matches faces in the photo against known students.

    IMPORTANT: uses a distance threshold AND a confidence margin.
    A plain "closest distance < 0.6" check can wrongly match a brand-new,
    unregistered face to whichever existing student happens to be nearest
    by chance. Requiring the best match to also be meaningfully closer
    than the second-best match (margin check) makes that far less likely,
    so new faces correctly fall through to registration instead of being
    logged in as someone else.
    """

    encodings = get_face_embeddings(class_image_np)

    detected_student = {}

    model_data = get_trained_model()

    if not model_data:
        return detected_student, [], len(encodings)

    x = model_data['x']
    y = model_data['y']

    DISTANCE_THRESHOLD = 0.55   # slightly stricter than before
    MIN_MARGIN = 0.08           # best match must beat 2nd-best by this much

    for encoding in encodings:

        # collect distances to every known embedding
        distances = [
            (np.linalg.norm(known_embedding - encoding), student_id)
            for known_embedding, student_id in zip(x, y)
        ]
        distances.sort(key=lambda d: d[0])

        best_distance, best_student = distances[0]
        second_distance = distances[1][0] if len(distances) > 1 else None

        print("MATCH:", best_student, "DISTANCE:", best_distance,
              "SECOND:", second_distance)

        is_confident_match = best_distance < DISTANCE_THRESHOLD and (
            second_distance is None or (second_distance - best_distance) >= MIN_MARGIN
        )

        if is_confident_match:
            detected_student[str(best_student)] = True

    return detected_student, list(set(y)), len(encodings)