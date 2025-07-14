# YouTube Transcript API Flask App

This is a simple Flask application that fetches YouTube video transcripts using the `youtube-transcript-api` package.

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   python youtube_script.py
   ```

## Running with Docker

1. Build the Docker image:
   ```bash
   docker build -t youtube-transcript-app .
   ```
2. Run the Docker container:
   ```bash
   docker run -p 5000:5000 youtube-transcript-app
   ```

The app will be available at [http://localhost:5000/transcript?url=YOUTUBE_URL](http://localhost:5000/transcript?url=YOUTUBE_URL)
