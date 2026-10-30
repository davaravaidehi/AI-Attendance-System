
 # AI Attendance System

An AI-powered web application that automates classroom attendance using **face recognition** and **voice attendance**. Teachers upload a single classroom photo, the system identifies every registered student in it, and attendance is saved automatically to a central database with ready-made reports.

---

## Features

- **Student registration** with details and a face image (face encoding stored securely in the database).
- **Teacher registration and login** with bcrypt-hashed passwords.
- **Subject management**: create subjects and share them with students through a code, link or QR code.
- **Face-based attendance**: upload or capture one classroom photo and identify multiple students at once.
- **Voice attendance** as an alternative when a classroom image is not suitable.
- **Unknown face handling**: unregistered faces are ignored instead of being matched to the wrong student.
- **Student portal**: students log in, enroll in subjects and view their attendance.
- **Reports**: student-wise, subject-wise and date-wise reports, low-attendance report, and CSV export.
- **Automatic attendance percentage**:

  ```
  Attendance % = (Classes Attended / Total Classes) x 100
  ```

---

## Tech Stack

| Technology | Purpose |
| --- | --- |
| **Python** | Main language for application logic |
| **Streamlit** | Web-based user interface |
| **OpenCV (cv2)** | Image processing (reading, colour conversion, resizing) |
| **face_recognition / dlib** | Face detection, 128-dimensional face encodings and face comparison |
| **SpeechRecognition** | Voice input for voice attendance |
| **NumPy** | Handling face encodings and distance calculations |
| **Pandas** | Filtering attendance data and generating reports |
| **Supabase (PostgreSQL)** | Cloud database for students, subjects and attendance |
| **Git / GitHub** | Version control |

---

## System Modules

1. **Student Registration** – collects student details and a face image, generates the face encoding and stores it in Supabase.
2. **Teacher / Attendance** – teacher login, subject selection and classroom image upload.
3. **AI Face Recognition** – processes the image with OpenCV, detects faces, generates encodings and matches them against registered                                students.
4. **Voice Attendance** – records the student's voice and matches it with registered students to mark attendance.
5. **Attendance and Report Management** – stores attendance records and generates reports and percentages.

---

## How It Works

**Student registration**

```
Student Details -> Face Image -> Face Detection -> Face Encoding -> Supabase
```

**Attendance process**

```
Teacher Login -> Select Subject -> Upload Classroom Image -> OpenCV Processing
-> Face Detection -> Face Encoding -> Compare with Registered Faces
-> Student Identification -> Mark Attendance -> Supabase
```

**Reporting**

```
Stored Attendance Data -> Pandas Processing -> Reports / Attendance Percentage
```

Each detected face is converted to a 128-value encoding and compared with the stored encodings by distance. If a close enough match is found the student is marked present; otherwise the face is treated as unknown.

---

## Database Design

The Supabase (PostgreSQL) database has five tables:

| Table | Description |
| --- | --- |
| `teachers` | Teacher login details (`teacher_id`, `username`, hashed `password`, `name`) |
| `students` | Registered students with `face_embedding` (128 values) and optional `voice_embedding` |
| `subjects` | Subject code, name, section and the assigned teacher |
| `subject_students` | Many-to-many link between subjects and enrolled students |
| `attenedence_logs` | One attendance record per student per session (`timestamp`, `subject_id`, `student_id`, `is_present`) |

> Note: the attendance table is spelled `attenedence_logs` in the database, so use this exact name in queries.

---

## Project Structure

```
Attendence_System_AI_project/
├── src/                # Application source modules
├── app.py              # Streamlit entry point
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python runtime version (for deployment)
├── .gitignore
└── README.md
```

---

## Installation and Setup

### Prerequisites

- Python 3.9 or higher (see `runtime.txt` for the exact version)
- A free [Supabase](https://supabase.com) account and project
- Webcam / microphone (optional, for live capture and voice attendance)
- Intel i3 or higher, 4 GB RAM or more

### 1. Clone the repository

```bash
git clone https://github.com/davaravaidehi/AI-Attendance-System.git
cd AI-Attendance-System
```

### 2. Create a virtual environment

```bash
python -m venv env

# Windows
env\Scripts\activate

# Linux / macOS
source env/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> `dlib` and `face_recognition` can take time to install. On Windows you may need CMake and Visual Studio C++ Build Tools.

### 4. Configure Supabase

Create the tables described in [Database Design](#database-design) in your Supabase project, then add your credentials in `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "your-project-url"
SUPABASE_KEY = "your-anon-or-service-key"
```

> Use the same key names that `app.py` / `src` read. **Never commit this file**; it is listed in `.gitignore`.

### 5. Run the app

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Usage

**Teacher**

1. Register and log in.
2. Create a subject and share its code, link or QR code with students.
3. Open **Take Attendance**, then upload or capture a classroom photo (or start a voice session).
4. Review the detected students on the confirmation screen and save.
5. View attendance records and download the CSV report.

**Student**

1. Register with details and a clear, single-face photo.
2. Log in and enroll in subjects using the subject code.
3. View your attendance on the student dashboard.

---

