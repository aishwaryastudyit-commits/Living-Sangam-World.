# 🌍 Living Sangam World: AI-Powered Immersive Tamil Poetry Experience

### Ancient Voices. Living Worlds. Powered by AI.

Living Sangam World is an AI-powered educational platform that transforms classical Tamil Sangam poetry into immersive visual, audio, and interactive experiences.

The platform combines literary analysis, scene generation, multilingual narration, OCR-based poem recognition, conversational AI, and multimedia storytelling to make Sangam literature accessible to modern learners while preserving its cultural richness.

---

# 📖 Problem Statement

Sangam literature is one of the world's oldest literary traditions and an invaluable part of Tamil cultural heritage. However, many learners face challenges in understanding and engaging with these works due to:

* Classical language complexity
* Limited historical and cultural context
* Lack of interactive learning tools
* Predominantly text-based educational resources

As a result, younger generations often struggle to connect with these timeless literary works.

---

# 💡 Solution

Living Sangam World reimagines Sangam literature through Artificial Intelligence.

Users can:

* Input or upload a Sangam poem
* Receive detailed literary analysis
* Explore the poem's emotional and cultural context
* Generate visual scene representations
* Listen to multilingual narrations
* Interact with an AI-powered Pulavar (Scholar)
* Experience poetry through an immersive learning journey

By combining AI with cultural heritage preservation, the platform transforms static literary content into an engaging and accessible educational experience.

---

# ✨ Core Features

## 📜 Pulavar Engine

AI-powered literary analysis that provides:

* Theme identification
* Emotional interpretation
* Thinai classification
* Cultural context
* Educational explanations

---

## 🎨 Scene Weaver

Transforms poetic descriptions into visual experiences by:

* Extracting key scenes
* Identifying landscapes
* Building visual representations
* Preserving cultural context

---

## 🎙 Sangam Voice

Provides multilingual narration of literary interpretations.

Supported narration languages include:

* Tamil
* English
* Hindi
* Malayalam
* Kannada
* Telugu

---

## 🤖 Pulavar AI

An interactive scholar capable of answering questions related to:

* Sangam poetry
* Literary meaning
* Symbolism
* Culture
* Historical context

---

## 📸 OCR-Based Poem Recognition

Allows users to upload poem images and automatically extract text for analysis.

Workflow:

Image → OCR → Analysis → Experience

---

## 🌐 Multilingual Experience

Designed to support learners from diverse linguistic backgrounds through multilingual narration and accessibility-focused learning experiences.

---

# 🏛 Heritage-Aware Design

Unlike generic literary analysis systems, Living Sangam World incorporates the classical Sangam landscape framework.

The platform recognizes the Five Traditional Tinais:

* 🌄 Kurunji (Mountains)
* 🌳 Mullai (Forests)
* 🌾 Marutham (Farmlands)
* 🌊 Neytal (Seashore)
* 🏜 Palai (Arid Lands)

This enables culturally grounded interpretations and visualizations that remain connected to the original literary tradition.

---

# ⚙️ Intelligent Cache & Fallback System

To ensure reliability even when external AI services are unavailable, Living Sangam World includes a built-in cache and fallback architecture.

### 📚 Library Assets

The platform maintains a curated library of heritage-aware assets that can be used whenever image generation or multimedia services are unavailable.

### 🖼 Scene Cache

The `scene_cache` contains pre-curated Thinai-specific images organized by landscape category:

* `kurunji/` – Mountain landscape cache images
* `mullai/` – Forest landscape cache images
* `marutham/` – Agricultural landscape cache images
* `neytal/` – Coastal landscape cache images
* `palai/` – Arid landscape cache images

When AI image generation fails or API limits are reached, the system automatically retrieves culturally relevant images from these folders to maintain a seamless user experience.

### 🎙 Audio Cache

The cache system stores generated narration audio files for supported languages. Previously generated narrations can be reused, reducing API calls and ensuring uninterrupted playback during fallback scenarios.

### ✅ Benefits

* Reduced dependency on external APIs
* Faster response times
* Reliable demonstrations during quota limitations
* Consistent Thinai-aware visual experiences
* Improved scalability and user experience

---

# ⚙️ System Workflow

```text
User Input
(Text / Library / Image)
          │
          ▼
     Pulavar Engine
          │
 ┌────────┼────────┐
 │        │        │
 ▼        ▼        ▼
Scenes   Voice   Pulavar AI
 │        │        │
 ▼        ▼        ▼
Images   Audio   Dialogue
          │
          ▼
  Immersive Experience
```

---

# 📂 Project Structure

```text
DTEC/
│
├── app.py
├── gemini_client.py
├── language_engine.py
├── ocr_engine.py
├── pulavar_ai.py
├── pulavar_engine.py
├── sangam_voice.py
├── scene_generator.py
├── scene_weaver.py
├── video_engine.py
├── schemas.py
├── poems.json
├── requirements.txt
│
├── assets/
│   ├── audio/
│   │   ├── analysis_narration_en.mp3
│   │   ├── analysis_narration_hi.mp3
│   │   ├── analysis_narration_kn.mp3
│   │   ├── analysis_narration_ml.mp3
│   │   ├── analysis_narration_ta.mp3
│   │   └── analysis_narration_te.mp3
│   │
│   └── images/
│       ├── cache/
│       ├── scene_cache/
│       │   ├── kurunji/
│       │   ├── mullai/
│       │   ├── marutham/
│       │   ├── neytal/
│       │   └── palai/
│       │
│       ├── kurunji/
│       ├── mullai/
│       ├── marutham/
│       ├── neytal/
│       └── palai/
│
├── generated_scenes/
├── outputs/
├── prompts/
└── tests/
```




---

# 🛠 Technology Stack

## Core Runtime

* Python 3.14.3
* Streamlit 1.58.0

---

## Frontend

* Streamlit

---

## Backend

* Python

---

## AI Models Used

### Gemini Text & Literary Analysis Models

* gemini-2.5-flash
* gemini-2.0-flash
* gemini-2.5-flash-lite

Used for:

* Poem analysis
* Literary interpretation
* Thinai classification
* Cultural context generation
* Scene breakdown generation
* Pulavar AI conversations

### Gemini OCR & Vision Models

* gemini-2.5-flash
* gemini-2.0-flash
* gemini-2.5-flash-lite

Used for:

* OCR-assisted poem extraction
* Image understanding
* Visual content interpretation

### Gemini Image Models

* gemini-2.5-flash-image
* gemini-3.1-flash-image
* gemini-3-pro-image

Used for:

* AI-generated scene creation
* Heritage-aware visual storytelling

### Stability AI Models

* stable-diffusion-xl-1024-v1-0

### Hugging Face Models

* stabilityai/stable-diffusion-xl-base-1.0

### OpenAI Models

#### Image Generation

* dall-e-3

#### Voice Generation

* tts-1

### ElevenLabs Models

#### Voice Narration

* eleven_multilingual_v2

---

## Multimedia

* Scene Generation Pipeline
* Audio Narration Pipeline
* Experience Video Generation

---

## Image Processing

* OCR Engine
* Gemini Vision Processing
* Optional Tesseract OCR Support

---

## Data

* JSON-Based Poem Repository
* Cached Thinai Asset Library

---

# 🔌 APIs & Environment Configuration

## Required API Key

```env
GEMINI_API_KEY=your_api_key_here
```



---

## Example Configuration

```env
# Required
GEMINI_API_KEY=

# Optional Google API
GOOGLE_API_KEY=

# Image Backend
IMAGE_BACKEND=auto

# Stability AI
STABILITY_API_KEY=

# OpenAI
OPENAI_API_KEY=

# Hugging Face
HF_TOKEN=

# TTS Backend
TTS_BACKEND=gtts

# ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

---

# 📦 Main Python Packages

Install all dependencies using:

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Important packages currently used by the project:

```text
streamlit==1.58.0
google-generativeai==0.8.5
google-genai==2.8.0
python-dotenv==1.2.2
gTTS==2.5.4
Pillow==11.3.0
pydantic==2.13.4
requests==2.34.2
httpx==0.28.1
moviepy==1.0.3
imageio==2.37.3
imageio-ffmpeg==0.6.0
numpy==2.4.6
pandas==3.0.3
opencv-python>=4.11.0
pytesseract>=0.3.13
huggingface-hub==1.18.0
openai==2.38.0
elevenlabs>=2.7.1
stability-sdk>=0.8.6
langdetect>=1.0.9
deep-translator>=1.11.4
pyyaml==6.0.3
```

---

# ⚠️ External Software Requirements

The following software should be installed separately and added to your system PATH:

## FFmpeg

Required for:

* Video rendering
* Audio processing
* Multimedia generation
* Subtitle and narration integration

Download:

https://ffmpeg.org/

---

## Tesseract OCR

Required for advanced OCR workflows.

Although the current implementation primarily uses Gemini Vision for OCR, Tesseract support is included through project dependencies.

Download:

https://github.com/tesseract-ocr/tesseract

---

# 🚀 Installation

Clone the repository:

```bash
git clone <repository-url>
cd DTEC
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the environment:

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Or:

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

# ⚠️ Important Setup Note

A version mismatch was identified during environment verification.

### Current Environment

```text
moviepy==1.0.3
```

### Required by requirements.txt

```text
moviepy>=2.1.2
```

### Recommended Upgrade

```bash
.\.venv\Scripts\python.exe -m pip install --upgrade moviepy imageio imageio-ffmpeg
```

This upgrade is strongly recommended for smoother video generation, rendering, and multimedia processing.

---

# ▶️ Run the Application

```bash
streamlit run app.py
```

---

# ✅ Recommended Production Setup

For the smoothest experience:

1. Install all packages from `requirements.txt`
2. Install FFmpeg and add it to PATH
3. Configure `GEMINI_API_KEY`
4. Use Gemini as the primary AI backend
5. Optionally configure Stability AI, OpenAI, Hugging Face, or ElevenLabs
6. Upgrade MoviePy to the latest supported version

This configuration provides the most reliable poem analysis, OCR, scene generation, narration, and multimedia rendering experience.

---

# 🎯 Educational Impact

Living Sangam World demonstrates how Artificial Intelligence can be used to preserve, teach, and revitalize cultural heritage.

The platform helps:

* Students learn classical literature
* Educators deliver engaging lessons
* Researchers explore literary contexts
* Communities preserve cultural knowledge
* Young learners connect with ancient Tamil traditions through modern technology

---

# 🚀 Future Scope

Living Sangam World is designed as a foundation for a larger AI-powered cultural heritage ecosystem.

Future enhancements include:

* Expanded Tamil literary collections
* Animated storytelling
* AI-generated cinematic experiences
* Additional multilingual support
* Scholar-reviewed literary datasets
* Virtual Reality (VR) heritage experiences
* Augmented Reality (AR) poem exploration
* Interactive Sangam-era maps
* Digital museum integrations
* Offline AI-assisted learning modules
* Educational dashboards and classroom integration

---

# 🌍 Vision

Living Sangam World seeks to bridge ancient wisdom and modern technology by transforming Sangam literature into immersive educational experiences.

Through analysis, narration, visualization, and interaction, the project ensures that the voices of Sangam poets continue to inspire future generations while making cultural heritage more accessible, engaging, and meaningful in the digital age.

---

# 👨‍💻 Developer

**Aishwarya Ravichandran**

Developed for DTEC Hackathon 2026

### "Preserving Heritage Through Intelligent Experiences."
