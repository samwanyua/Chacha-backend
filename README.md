# Chacha: AI-Powered Speech Support for Children

![Chacha Logo](https://img.shields.io/badge/Chacha-SpeechMaster-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch)

## 1. Problem Statement

Millions of young children experience speech impairments or delayed speech development, making it difficult for them to communicate clearly in everyday interactions. However, access to speech therapy is limited, expensive, and often unavailable, especially in schools and homes. Without consistent practice and feedback, children struggle to improve their pronunciation, participate in learning activities, and build confidence in communication.

As a result, many children fall behind academically and socially because they lack accessible tools to practice and improve their speech.

### Targeting Speech Impairments (Mild to Moderate):

#### **Mild Speech Impairments**
These cause minor difficulties but allow most communication without significant effort:
- **Lisp** – Difficulty pronouncing “s” and “z” sounds.
- **Mild articulation disorders** – Slight mispronunciations (e.g., “r” or “th”).
- **Mild stuttering** – Occasional repetition of sounds or words.
- **Voice disorders** – Slight pitch or volume irregularities.

#### **Moderate Speech Impairments**
These make communication noticeably harder and may require support:
- **Moderate stuttering** – Frequent repetitions, prolongations, or blocks.
- **Phonological disorders** – Patterns of sound errors affecting multiple sounds consistently.
- **Apraxia of speech** – Difficulty planning and coordinating movements needed for speech.
- **Dysarthria** – Weakness or poor coordination of speech muscles, causing slurred speech.


## 2. The Solution

**Chacha** is an AI-powered speech support tool designed to help children practice speaking and improve pronunciation through interactive, engaging exercises. By acting as a virtual speech practice partner, Chacha bridges the gap between limited therapy sessions and daily home/classroom practice.

The system listens to a child’s speech, analyzes pronunciation in real-time, and provides immediate feedback. It empowers teachers, therapists, and parents with data-driven tools to track progress and guide the child's learning journey.

---

## 3. Our Approach

Our platform uses state-of-the-art AI speech recognition and pronunciation analysis models:

1.  **Listening**: Captures high-quality audio of children pronouncing targeted words or sounds.
2.  **Analyzing**: Uses customized speech recognition models to evaluate accuracy against target phonemes.
3.  **Feedback**: Provides instant confidence scores and visual cues to guide improvement.
4.  **Gamification**: Offers interactive exercises and games to encourage consistent daily practice.
5.  **Monitoring**: Detailed progress tracking for parents and professionals to monitor long-term improvement.

---

## 4. Key Differentiators

While several tools exist globally, Chacha focuses on:
- **Child-Centric Design**: Tailored specifically for the speech patterns and engagement styles of young learners.
- **Adaptive AI Models**: Designed to learn and adapt to diverse speech patterns, including those often missed by general-purpose AI.
- **Inclusive Accessibility**: Built to work in diverse environments, ensuring children from various backgrounds can participate.
- **Professional Integration**: Directly supports therapists and teachers by providing them with actionable insights from at-home practice.

---

## 5. Technology Stack (Backend)

The **Chacha Backend** (SpeechMaster) is a high-performance API built with modern Python technologies:

-   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) for high-speed, asynchronous API endpoints.
-   **Speech-to-Text (STT)**: Integration with HuggingFace Transformers and PyTorch for accurate transcription and analysis.
-   **Text-to-Speech (TTS)**: [Piper-TTS](https://github.com/rhasspy/piper) for natural-sounding voice guidance.
-   **Scoring Engine**: Custom algorithms using Levenshtein distance and WER (Word Error Rate) for pronunciation evaluation.
-   **Database**: SQLite/PostgreSQL for tracking user attempts, history, and progress stats.

---

## 6. Getting Started

### Prerequisites
- Python 3.9 or higher
- `pip` or `conda`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd chacha-backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv env
    source env/bin/activate  # On Windows use: env\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. You can access the interactive Swagger documentation at `http://localhost:8000/docs`.

---

## 7. Market Context & Similar Solutions

Chacha joins a global movement to democratize speech therapy:
-   **Otsimo Speech Therapy**: Uses AI for articulation practice in children with autism or speech delays.
-   **Speech Blubs**: Focuses on video modeling and voice recognition through play.
-   **Better Speech**: Connects users with remote licensed therapists.
-   **Signverse (Kenya)**: A regional pioneer translating speech into sign language for inclusion.

---

## 8. API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/auth/register` | `POST` | Create a new user account. |
| `/api/sentences` | `GET` | Fetch practice sentences by difficulty level. |
| `/api/recordings/evaluate`| `POST` | Upload audio and evaluate pronunciation accuracy. |
| `/api/tts` | `POST` | Generate speech from text for guidance. |
| `/api/users/{id}/stats` | `GET` | Retrieve user performance statistics and history. |

---
## 9. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
