import os
import time
import logging
import subprocess
from text_to_audio import text_to_speech_with_gtts
from pydub import AudioSegment

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Track failed attempts
FAILED_ATTEMPTS_FILE = "failed_attempts.txt"
MAX_ATTEMPTS = 3

def load_failed_attempts():
    try:
        with open(FAILED_ATTEMPTS_FILE, "r", encoding='utf-8') as f:
            return {line.strip().split(":")[0]: int(line.strip().split(":")[1]) for line in f if ":" in line}
    except FileNotFoundError:
        return {}

def save_failed_attempt(folder, attempts):
    failed_attempts = load_failed_attempts()
    failed_attempts[folder] = attempts
    with open(FAILED_ATTEMPTS_FILE, "w", encoding='utf-8') as f:
        for folder_id, count in failed_attempts.items():
            f.write(f"{folder_id}:{count}\n")

def generate_reel(folder):
    audio_file = os.path.normpath(os.path.join("user_upload", folder, "audio.mp3"))
    output_file = os.path.normpath(os.path.join("static", "reels", f"{folder}.mp4"))
    thumbnail_file = os.path.normpath(os.path.join("static", "reels", "thumbnails", f"{folder}.jpg"))
    input_file = os.path.normpath(os.path.join("user_upload", folder, "input.txt"))

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

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.makedirs(os.path.dirname(thumbnail_file), exist_ok=True)

    # Generate reel
    command = (
        f'ffmpeg -stream_loop -1 -f concat -safe 0 -i "{input_file}" -i "{audio_file}" '
        f'-vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" '
        f'-c:v libx264 -c:a aac -shortest -r 30 -pix_fmt yuv420p "{output_file}"'
    )
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        logging.info(f"Reel generated successfully: {output_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error (reel generation): {e.stderr}")
        return False

    # Generate thumbnail
    thumbnail_command = (
        f'ffmpeg -i "{output_file}" -vframes 1 -vf "scale=320:180:force_original_aspect_ratio=decrease" '
        f'"{thumbnail_file}"'
    )
    try:
        subprocess.run(thumbnail_command, shell=True, capture_output=True, text=True, check=True)
        logging.info(f"Thumbnail generated successfully: {thumbnail_file}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error (thumbnail generation): {e.stderr}")
        return False

if __name__ == "__main__":
    while True:
        logging.info("Processing folders...")
        try:
            with open("done.txt", "r", encoding='utf-8') as f:
                done_folders = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            done_folders = []

        failed_attempts = load_failed_attempts()
        folders = os.listdir("user_upload")
        for folder in folders:
            if folder in done_folders:
                logging.info(f"Skipping already processed folder: {folder}")
                continue
            if folder in failed_attempts and failed_attempts[folder] >= MAX_ATTEMPTS:
                logging.warning(f"Skipping folder {folder}: Max attempts ({MAX_ATTEMPTS}) reached")
                continue

            logging.info(f"Processing folder: {folder}")
            dec_file = os.path.normpath(os.path.join("user_upload", folder, "dec.txt"))
            if not os.path.exists(dec_file):
                logging.warning(f"No dec.txt found in folder {folder}. Skipping.")
                continue
            with open(dec_file, "r", encoding='utf-8') as f:
                input_text = f.read().strip()
            if not input_text:
                logging.warning(f"No text in dec.txt for folder {folder}. Skipping.")
                continue

            audio_filepath = text_to_speech_with_gtts(input_text, folder)
            if audio_filepath:
                if generate_reel(folder):
                    with open("done.txt", "a", encoding='utf-8') as f:
                        f.write(f"{folder}\n")
                    logging.info(f"Completed processing folder: {folder}")
                    if folder in failed_attempts:
                        del failed_attempts[folder]
                        save_failed_attempt(folder, 0)
                else:
                    logging.error(f"Failed to generate reel for folder: {folder}")
                    failed_attempts[folder] = failed_attempts.get(folder, 0) + 1
                    save_failed_attempt(folder, failed_attempts[folder])
            else:
                logging.error(f"Failed to generate audio for folder: {folder}")
                failed_attempts[folder] = failed_attempts.get(folder, 0) + 1
                save_failed_attempt(folder, failed_attempts[folder])
        time.sleep(5)  # Increased delay to prevent overloading