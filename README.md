TibiaVision Platform
This document outlines the technical specifications for the TibiaVision Analytics Platform, a comprehensive tool for processing and analyzing Tibia gameplay videos.

TibiaVision.AI.CreateLabel
This section contains the complete technical prompt for generating the TibiaVision application. It describes a self-contained, containerized web application designed for batch video analysis.

Prompt Inputs & Outputs
Inputs: The system is designed to accept video data from three distinct sources:

Local File Upload: A video file (e.g., .mp4, .avi) uploaded directly from the user's computer.

Direct URL: A public URL pointing directly to a video file.

YouTube URL: A standard link to a YouTube video.
Additionally, the user provides a "frame skip" value to control the analysis sampling rate.

Outputs: The application processes the input video and generates a structured dataset consisting of:

Image Frames: Individual video frames that were analyzed, saved as .png files.

JSON Labels: A single labels.jsonl file where each line is a JSON object containing the extracted data for the corresponding frame (player coordinates, stats, battle list entities, etc.).
The output is stored in a unique, timestamped directory for each analysis job.

### Comprehensive Prompt: Containerized "TibiaVision" Web Application for Video Analysis from Files, URLs, and YouTube

**Project Title:** TibiaVision Analytics Platform

**Objective:** To create a complete, multi-file, and containerized web application in Python (using the Flask framework) that allows users to log in, submit Tibia gameplay videos, and run an automated batch analysis process. The application must support three video sources: **uploading a local file, providing a direct URL (e.g., to an .mp4 file), and providing a link to a YouTube video**. The entire system must be packaged using Docker and Docker Compose to ensure a simple, single-command installation and launch of the environment.

**System Architecture:**

1.  **Backend (Python/Flask):** The core of the application. It is responsible for user authentication, handling various video sources (upload, URL, YouTube), managing background analysis tasks, and delivering results to the frontend.
2.  **Frontend (HTML/CSS/JavaScript):** The user interface running in the browser, enabling interaction with the backend (login, video source selection, progress monitoring).
3.  **Containerization (Docker):** The entire application, along with its dependencies (Python, OpenCV, EasyOCR, yt-dlp, FFmpeg), will be encapsulated in a Docker image, and `docker-compose.yml` will orchestrate its launch.

---

#### Detailed Technical Specification

##### 1. Project Structure (File Tree)

The generated code should have the following structure:


tibia-vision-app/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── map.png  <-- World map file, to be added by the user
│
└── app/
├── init.py
├── main.py        <-- Main Flask application file
├── auth.py        <-- Authentication logic
├── analysis.py    <-- Core logic for video analysis and downloading
│
├── static/
│   └── style.css  <-- (Optional) additional styles
│
└── templates/
├── login.html
└── dashboard.html


##### 2. Backend (Flask Framework)

* **Authentication (`app/auth.py`):**
    * Implement a simple user session using `flask-login`. For simplicity, login credentials can be hardcoded (e.g., `admin`/`password`).
    * Secure the application's endpoints to require a logged-in session.

* **Routing (`app/main.py`):**
    * `/`, `/login`, `/logout`: Standard endpoints for session management.
    * `/dashboard`: Displays the main application dashboard.
    * `/start_analysis` (POST): A key endpoint that accepts a JSON payload: `{"source_type": "upload|url|youtube", "source_data": "filename_or_url", "frame_skip": N}`. It must start the analysis process in a **separate background thread** to avoid blocking the application and should return a unique `job_id`.
    * `/status/<job_id>` (GET): An endpoint for polling the status of a job. It should return a JSON object with the progress (e.g., `{"progress": 25, "status": "Processing frame 1200/4800"}`).

* **Analysis and Download Logic (`app/analysis.py`):**
    * **`download_video(source_type, source_data, target_path)` function:**
        * Implements the video download logic.
        * For `source_type == 'url'`: Uses the `requests` library to download the file and save it to `target_path`.
        * For `source_type == 'youtube'`: Uses the `yt-dlp` library to download the best quality video stream and save it to `target_path`.
    * **Main `run_analysis(source_type, source_data, frame_skip, job_id)` function:**
        1.  Initially, it calls `download_video` to obtain a local copy of the video file in a dedicated `uploads/JOB_ID/` folder.
        2.  It then executes the analysis logic: opens the local video file, iterates through frames with `frame_skip`, performs image analysis on each selected frame, and saves the results.
        3.  It must regularly update the job status (progress, current activity).

##### 3. Frontend (HTML/JavaScript)

* **`templates/login.html`:** A simple, centered login form.
* **`templates/dashboard.html`:**
    * **Input Section:**
        * Implement an interface with **three tabs**: "Upload File," "Direct URL," and "YouTube Link."
        * Display the appropriate input field based on the selected tab (`<input type="file">` or `<input type="text">`).
        * Include a shared number input field for "Frame Skip."
        * A single "Start Analysis" button.
    * **Jobs Section:** A dynamic table or list to display the status of ongoing and completed analysis jobs.
    * **JavaScript Logic:**
        * Manage the tab switching in the UI.
        * Handle the "Start Analysis" button click: the script must check the active tab, retrieve the appropriate data (file or URL text), and send it to the `/start_analysis` endpoint in the correct JSON format.
        * Implement periodic polling (every 2-3 seconds) of the `/status/<job_id>` endpoint and update the progress bar and status text on the page accordingly.

##### 4. Containerization (Docker)

* **`requirements.txt`:**
    * The file must include all Python dependencies: `Flask`, `Flask-Login`, `opencv-python`, `numpy`, `easyocr`, `gunicorn`, **`yt-dlp`**, **`requests`**.

* **`Dockerfile`:**
    * Use an official base image, e.g., `python:3.9-slim`.
    * **Install system dependencies:** In addition to the standard libraries for OpenCV, **it is crucial to add `ffmpeg`**, which is required by `yt-dlp` for processing video streams.
        ```dockerfile
        RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 ffmpeg
        ```
    * Copy `requirements.txt` and install dependencies via `pip`.
    * Copy the application code and the `map.png` file into the image.
    * Define the startup command using `gunicorn` to serve the Flask application (e.g., `CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.main:app"]`).

* **`docker-compose.yml`:**
    * Define a single service named `web`.
    * `build: .` - Indicates that the service should be built from the `Dockerfile` in the current directory.
    * `ports:` - Map the container port to a host port, e.g., `"8080:5000"`.
    * `volumes:` - Define volumes for persistent data storage, so data is not lost on container restart:
        * `./uploads:/app/uploads`
        * `./output:/app/output`
