import os
import requests
from flask import Flask, render_template, request, jsonify, send_from_directory
from moviepy.editor import VideoFileClip, ImageClip
from tempfile import NamedTemporaryFile
import time
from threading import Thread
from PIL import Image


app = Flask(__name__)

# Path where videos and processed files are stored
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

# Function to download video from URL
def download_video(url):
    temp_file = NamedTemporaryFile(delete=False, suffix='.mp4')
    temp_file.close()
    response = requests.get(url)
    if response.status_code == 200:
        with open(temp_file.name, 'wb') as f:
            f.write(response.content)
        return temp_file.name
    else:
        raise Exception(f"Failed to download video: {response.status_code}")

def add_logo_to_video(video_path, logo_path, output_path, progress_callback):
    video_clip = VideoFileClip(video_path)

    # Open the logo with Pillow
    logo_image = Image.open(logo_path)
    
    # Resize the logo with Pillow using the resample argument
    logo_image = logo_image.resize((logo_image.width, 50), resample=Image.Resampling.LANCZOS)
    
    # Save the resized logo to a temporary file
    resized_logo_path = 'resized_logo.png'
    logo_image.save(resized_logo_path)

    # Create an ImageClip from the resized logo
    logo = ImageClip(resized_logo_path)
    logo = logo.set_position(("right", "top")).set_duration(video_clip.duration)
    
    # Simulating progress
    total_frames = video_clip.reader.nframes
    processed_frames = 0
    
    def frame_process(image):
        nonlocal processed_frames
        processed_frames += 1
        progress_callback(processed_frames / total_frames * 100)
        return image
    
    video_with_logo = video_clip.fl_image(frame_process)
    final_video = video_clip.set_audio(video_clip.audio).overlay(logo)
    final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    # Final progress update
    progress_callback(100)

# Function to add a logo to the video

# API route to process the video
@app.route('/process-video', methods=['POST'])
def process_video():
    video_url = request.json.get("video_url")
    output_file = os.path.join(PROCESSED_FOLDER, "output_video.mp4")
    logo_file = "logo.png"
    
    def progress_callback(progress):
        # Broadcasting progress to the frontend could be done with websockets or similar
        # For now, we'll just store the progress in a file as a workaround
        with open('progress.txt', 'w') as f:
            f.write(str(progress))

    try:
        video_path = download_video(video_url)
        add_logo_to_video(video_path, logo_file, output_file, progress_callback)
        return jsonify({"message": "Video processed successfully", "output_file": output_file})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Serve the frontend
@app.route('/')
def index():
    return render_template('index.html')

# Serve progress updates (this can be improved with websockets for real-time progress)
@app.route('/progress')
def progress():
    try:
        with open('progress.txt', 'r') as f:
            progress = float(f.read())
        return jsonify({"progress": progress})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Serve processed video file
@app.route('/processed/<filename>')
def download_processed(filename):
    return send_from_directory(PROCESSED_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
