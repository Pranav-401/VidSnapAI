import os
import logging
from gtts import gTTS
from pydub import AudioSegment

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def text_to_speech_with_gtts(input_text, folder, lang='en-us'):
    if not isinstance(input_text, str) or not input_text.strip():
        logging.error("Invalid input: Text must be a non-empty string")
        return None

    target_dir = os.path.normpath(os.path.join("user_upload", folder))
    os.makedirs(target_dir, exist_ok=True)
    output_filepath = os.path.normpath(os.path.join(target_dir, "audio.mp3"))

    logging.info(f"Generating audio for text: {input_text[:50]}... in folder {folder}")

    try:
        tts = gTTS(text=input_text, lang=lang, slow=False)
        tts.save(output_filepath)
        if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
            try:
                AudioSegment.from_mp3(output_filepath)
                logging.info(f"Audio file {output_filepath} generated successfully")
                return output_filepath
            except Exception as e:
                logging.error(f"Invalid MP3 file generated: {e}")
                if os.path.exists(output_filepath):
                    os.remove(output_filepath)
                return None
        else:
            logging.error(f"Audio file {output_filepath} is empty or does not exist")
            if os.path.exists(output_filepath):
                os.remove(output_filepath)
            return None
    except Exception as e:
        logging.error(f"gTTS error: {e}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return None