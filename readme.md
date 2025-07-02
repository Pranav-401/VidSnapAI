# VidSnapAI 🎬🤖

VidSnapAI is an AI-powered video reel generator that takes user-uploaded images and text, converts the text into speech, and automatically stitches everything into short video reels suitable for social media.

## ✨ Features

- Upload multiple images
- Provide descriptive text
- Automatically generate voiceover using ElevenLabs TTS (or another engine)
- Combine images and voiceover into a vertical video reel (1080x1920)
- Supports .png, .jpg, .jpeg images
- Output in MP4 format with H.264 encoding
- Automatic folder-based queue processing

## 🛠 Tech Stack

- **Python** (Flask backend)
- **FFmpeg** for video generation
- **ElevenLabs API** for text-to-speech
- **Pydub** for audio processing
- **dotenv** for secure API key storage
- HTML / CSS / JavaScript for the simple web front-end

## 📂 Project Structure

.
├── app.py # Flask server to handle uploads
├── generate_process.py # Background processor to monitor and generate reels
├── text_to_audio.py # ElevenLabs TTS integration
├── user_upload/ # Stores uploaded images and generated files
├── static/reels/ # Stores final MP4 reels
├── templates/
│ ├── index.html
│ ├── create.html
│ └── gallery.html
├── .env # API key (not committed)
└── README.md

bash
Copy
Edit

## 🚀 How to Run

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/VidSnapAI.git
cd vidsnapai
Install dependencies

bash
Copy
Edit
pip install -r requirements.txt
Set up your environment variables

Create a .env file:

env
Copy
Edit
ELEVENLABS_API_KEY=your_api_key_here
Run the Flask server

bash
Copy
Edit
python app.py
Run the background reel generator

In another terminal:

bash
Copy
Edit
python generate_process.py
Visit the app

Go to:
http://127.0.0.1:5000

Upload your images and text, and the background worker will generate your reel automatically.

⚠️ Known Issues
ElevenLabs free tier may block repeated or automated requests. Consider a paid subscription or use another TTS (e.g., Coqui TTS).

Filenames with spaces must be carefully handled (already quoted in input.txt).

Only tested on Windows — cross-platform playback needs verification.

🎯 Future Plans
Add background music support

Provide user authentication

Integrate with social sharing APIs

Support local offline TTS with Coqui

Progress tracking in the UI

📜 License
This project is licensed under the MIT License.

Happy creating with VidSnapAI! 🚀

yaml
Copy
Edit

---

If you want, I can also help you convert this into a **requirements.txt** or even prepare a **deployment guide** (like for Heroku or Doc
```
