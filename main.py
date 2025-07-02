import os
import uuid
import subprocess
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import logging
from PIL import Image
from gtts import gTTS
from pydub import AudioSegment

# Setup logging to file and console
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Check FFmpeg availability
def check_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, check=True)
        logging.info(f"FFmpeg version: {result.stdout.splitlines()[0]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"FFmpeg not found or failed: {e}")
        return False

if not check_ffmpeg():
    logging.error("FFmpeg is required but not found. Please install FFmpeg and ensure it's in PATH.")
    exit(1)

# Flask app setup
UPLOAD_FOLDER = 'user_upload'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload and static folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join('static', 'reels', 'thumbnails'), exist_ok=True)
os.makedirs(os.path.join('static', 'images'), exist_ok=True)

def text_to_speech_with_gtts(input_text, folder, lang='en', tld='us'):
    if not isinstance(input_text, str) or not input_text.strip():
        logging.error("Invalid input: Text must be a non-empty string")
        return None

    target_dir = os.path.join("user_upload", folder)
    os.makedirs(target_dir, exist_ok=True)
    output_filepath = os.path.join(target_dir, "audio.mp3")

    logging.info(f"Generating audio for text: {input_text[:50]}... in folder {folder}")

    try:
        tts = gTTS(text=input_text, lang=lang, tld=tld, slow=False)
        tts.save(output_filepath)
        if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
            try:
                AudioSegment.from_mp3(output_filepath)
                logging.info(f"Audio file {output_filepath} generated and validated successfully")
                return output_filepath
            except Exception as e:
                logging.error(f"Invalid MP3 file generated at {output_filepath}: {e}")
                if os.path.exists(output_filepath):
                    os.remove(output_filepath)
                return None
        else:
            logging.error(f"Audio file {output_filepath} is empty or does not exist")
            if os.path.exists(output_filepath):
                os.remove(output_filepath)
            return None
    except Exception as e:
        logging.error(f"gTTS error: {e}, text: {input_text}, folder: {folder}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return None

def generate_reel(folder):
    audio_file = os.path.join("user_upload", folder, "audio.mp3")
    output_file = os.path.join("static", "reels", f"{folder}.mp4")
    thumbnail_file = os.path.join("static", "reels", "thumbnails", f"{folder}.jpg")  # Fixed syntax error
    input_file = os.path.join("user_upload", folder, "input.txt")

    # Verify required files
    if not os.path.exists(audio_file):
        logging.error(f"Audio file {audio_file} does not exist")
        return False
    if not os.path.exists(input_file):
        logging.error(f"Input file {input_file} does not exist")
        return False

    # Verify audio file
    try:
        AudioSegment.from_mp3(audio_file)
        logging.info(f"Validated audio file: {audio_file}")
    except Exception as e:
        logging.error(f"Invalid audio file {audio_file}: {e}")
        return False

    # Verify input.txt content and image files
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            input_content = f.read()
        if not input_content.strip():
            logging.error(f"Input file {input_file} is empty")
            return False
        logging.info(f"Input file content: {input_content}")
        for line in input_content.split('\n'):
            if line.startswith("file '"):
                image_file = line.split("'")[1]
                image_path = os.path.join("user_upload", folder, image_file)
                if not os.path.exists(image_path):
                    logging.error(f"Image file {image_path} does not exist")
                    return False
                try:
                    Image.open(image_path).verify()
                    logging.info(f"Validated image file: {image_path}")
                except Exception as e:
                    logging.error(f"Invalid image file {image_path}: {e}")
                    return False
    except Exception as e:
        logging.error(f"Error reading input file {input_file}: {e}")
        return False

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.makedirs(os.path.dirname(thumbnail_file), exist_ok=True)

    # Simplified FFmpeg command
    command = (
        f'ffmpeg -f concat -safe 0 -i "{input_file}" -i "{audio_file}" '
        f'-vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30" '
        f'-c:v libx264 -c:a aac -shortest -pix_fmt yuv420p "{output_file}"'
    )
    logging.info(f"Running FFmpeg command: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        logging.info(f"Reel generated successfully: {output_file}")
        logging.debug(f"FFmpeg output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error (reel generation): {e.stderr}")
        return False

    # Verify reel file exists
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        logging.error(f"Reel file {output_file} was not created or is empty")
        return False

    # Generate thumbnail
    thumbnail_command = (
        f'ffmpeg -i "{output_file}" -vframes 1 -vf "scale=320:180:force_original_aspect_ratio=decrease" '
        f'"{thumbnail_file}"'
    )
    logging.info(f"Running FFmpeg thumbnail command: {thumbnail_command}")
    try:
        result = subprocess.run(thumbnail_command, shell=True, capture_output=True, text=True, check=True)
        logging.info(f"Thumbnail generated successfully: {thumbnail_file}")
        logging.debug(f"FFmpeg thumbnail output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error (thumbnail generation): {e.stderr}")
        return False

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/create", methods=["GET", "POST"])
def create():
    myid = str(uuid.uuid1())
    
    if request.method == "POST":
        rec_id = request.form.get("uuid") or myid
        desc = request.form.get("text")
        input_files = []

        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], rec_id)
        os.makedirs(folder_path, exist_ok=True)

        # Handle dynamic file inputs (file1, file2, etc.)
        for key in request.files:
            if key.startswith('file') and request.files[key].filename:
                file = request.files[key]
                filename = secure_filename(file.filename)
                if filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
                    file_path = os.path.join(folder_path, filename)
                    try:
                        file.save(file_path)
                        if os.path.exists(file_path):
                            try:
                                Image.open(file_path).verify()
                                input_files.append(filename)
                                logging.info(f"Saved and validated file: {file_path}")
                            except Exception as e:
                                logging.error(f"Invalid image file {file_path}: {e}")
                                os.remove(file_path)
                                return render_template("create.html", id=myid, error=f"Invalid image file {filename}: {e}")
                        else:
                            logging.error(f"File {file_path} was not saved")
                            return render_template("create.html", id=myid, error=f"Failed to save file {filename}.")
                    except Exception as e:
                        logging.error(f"Failed to save file {filename}: {e}")
                        return render_template("create.html", id=myid, error=f"Failed to save file {filename}: {e}")
                else:
                    logging.warning(f"File {filename} not allowed. Skipping.")

        if not input_files:
            logging.error("No valid image files uploaded.")
            return render_template("create.html", id=myid, error="Please upload at least one valid image file (PNG, JPG, JPEG).")

        if not desc or not desc.strip():
            logging.error("No description provided.")
            return render_template("create.html", id=myid, error="Please provide a description for the reel.")

        # Save the description
        desc_file = os.path.join(folder_path, "dec.txt")
        try:
            with open(desc_file, "w", encoding='utf-8') as f:
                f.write(desc)
            logging.info(f"Saved description to {desc_file}")
        except Exception as e:
            logging.error(f"Failed to save description to {desc_file}: {e}")
            return render_template("create.html", id=myid, error=f"Failed to save description: {e}")

        # Write input.txt with relative filenames
        input_file = os.path.join(folder_path, "input.txt")
        try:
            with open(input_file, "w", encoding='utf-8') as f:
                for fl in input_files:
                    f.write(f"file '{fl}'\n")
                    f.write("duration 2\n")  # Increased duration for better visibility
            logging.info(f"Created input.txt with {len(input_files)} images")
        except Exception as e:
            logging.error(f"Failed to create input.txt: {e}")
            return render_template("create.html", id=myid, error=f"Failed to create input file: {e}")

        # Generate audio
        audio_filepath = text_to_speech_with_gtts(desc, rec_id, lang='en', tld='us')
        if not audio_filepath:
            logging.error("Failed to generate audio.")
            return render_template("create.html", id=myid, error="Failed to generate audio for the reel. Check network or logs.")

        # Generate thumbnail from the first image
        thumbnail_path = os.path.join('static', 'reels', 'thumbnails', f"{rec_id}.jpg")
        try:
            with Image.open(os.path.join(folder_path, input_files[0])) as img:
                img.thumbnail((200, 200))
                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                img.save(thumbnail_path, "JPEG")
            logging.info(f"Generated thumbnail at {thumbnail_path}")
        except Exception as e:
            logging.error(f"Failed to generate thumbnail for {rec_id}: {e}")
            return render_template("create.html", id=myid, error=f"Failed to generate thumbnail: {e}")

        # Generate reel
        if not generate_reel(rec_id):
            logging.error("Failed to generate reel.")
            return render_template("create.html", id=myid, error="Failed to generate reel video. Check FFmpeg installation or logs.")

        # Verify reel exists
        output_file = os.path.join("static", "reels", f"{rec_id}.mp4")
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            logging.error(f"Reel file {output_file} not found or is empty after generation.")
            return render_template("create.html", id=myid, error="Reel file was not created. Check logs for details.")

        logging.info(f"Created reel {rec_id} successfully")
        return render_template("create.html", id=myid, success=True)

    return render_template("create.html", id=myid)

@app.route("/gallery")
def gallery():
    reels_dir = os.path.join("static", "reels")
    os.makedirs(reels_dir, exist_ok=True)
    reels = []
    fallback_thumbnail = os.path.join("images", "fallback.jpg").replace(os.sep, "/")

    # Ensure fallback image exists
    fallback_path = os.path.join("static", fallback_thumbnail)
    if not os.path.exists(fallback_path):
        from PIL import Image, ImageDraw
        os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
        img = Image.new("RGB", (200, 200), color="grey")
        d = ImageDraw.Draw(img)
        d.text((10, 90), "No Thumbnail", fill="white")
        img.save(fallback_path, "JPEG")
        logging.info(f"Created default fallback thumbnail at {fallback_path}")

    for f in os.listdir(reels_dir):
        if f.endswith(".mp4"):
            folder_id = f.replace(".mp4", "")
            dec_file = os.path.join("user_upload", folder_id, "dec.txt")
            thumbnail = os.path.join("reels", "thumbnails", f"{folder_id}.jpg").replace(os.sep, "/")
            thumbnail_path = os.path.join("static", thumbnail)

            thumbnail_rel_path = thumbnail if os.path.exists(thumbnail_path) else fallback_thumbnail
            title = "Untitled"
            try:
                if os.path.exists(dec_file):
                    with open(dec_file, "r", encoding='utf-8') as df:
                        title = df.read().strip()[:50] or "Untitled"
            except Exception as e:
                logging.error(f"Error reading description file {dec_file}: {e}")
            reels.append({
                "file": f,
                "title": title,
                "thumbnail": thumbnail_rel_path,
                "creator": "Anonymous"
            })
            logging.info(f"Added reel {f} to gallery with thumbnail: /static/{thumbnail_rel_path}")
    logging.info(f"Files in reels_dir: {os.listdir(reels_dir)}")
    logging.info(f"Found {len(reels)} reels in {reels_dir}")
    return render_template("gallery.html", reels=reels, folder="reels")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)