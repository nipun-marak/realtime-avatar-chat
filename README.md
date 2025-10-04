# RealTime Avatar Chat with Viseme Lip Sync

A sophisticated AI-powered chat application featuring a realistic avatar with real-time viseme-based lip synchronization. The avatar's mouth movements are synchronized with AI-generated speech, creating an immersive conversational experience.

## 🎭 Features

### Core Functionality
- **AI Chat Interface**: Powered by Google Gemini for intelligent conversations
- **Voice Synthesis**: High-quality text-to-speech using ElevenLabs API
- **Speech Recognition**: Voice input support with real-time transcription
- **User Memory**: Persistent conversation history and user preferences

### Avatar & Lip Sync
- **Real-time Viseme Lip Sync**: Avatar mouth movements synchronized with speech
- **6 Viseme Types**: Silence, Bilabial (P/B/M), Alveolar (T/D/N), Open Vowel (A/E), Close Front (I), Close Back (U/O)
- **Precise Timing**: 50ms update intervals for smooth lip synchronization
- **Dynamic Avatar States**: Idle, Listening, Thinking, Speaking states with visual feedback

### User Interface
- **Modern Web UI**: Clean, responsive design with real-time updates
- **Fullscreen Mode**: Immersive chat experience
- **Voice Controls**: Toggle voice output and speech recognition
- **Session Management**: Persistent user sessions with smart greetings

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)
- Google Gemini API key
- ElevenLabs API key (optional, for voice features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/realtime-avatar-chat.git
   cd realtime-avatar-chat
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env_example.txt .env
   # Edit .env with your API keys
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and go to `http://localhost:5001`

## 🔧 Configuration

### Environment Variables
Create a `.env` file with the following variables:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (for voice features)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional (default values shown)
DEBUG=True
HOST=0.0.0.0
PORT=5001
DB_NAME=companion.db
```

### API Keys Setup

1. **Google Gemini API**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Add it to your `.env` file

2. **ElevenLabs API** (Optional)
   - Visit [ElevenLabs](https://elevenlabs.io/)
   - Sign up and get your API key
   - Add it to your `.env` file

## 🎯 How It Works

### Viseme Lip Sync System

The application uses a sophisticated phoneme-to-viseme mapping system:

1. **Text Analysis**: Converts user input to phonemes using rule-based mapping
2. **Viseme Mapping**: Maps phonemes to appropriate mouth shapes (visemes)
3. **Timing Calculation**: Calculates precise timing for each viseme frame
4. **Real-time Sync**: Updates avatar image in real-time during speech

### Viseme Types
- **Silence (0)**: Neutral/closed mouth
- **Bilabial (1)**: Lips together (P, B, M sounds)
- **Labiodental (2)**: Lip to teeth (F, V sounds)
- **Linguolabial (3)**: Tongue to lips (TH sounds)
- **Alveolar (4)**: Tongue to roof (T, D, N, S, L, R sounds)
- **Palatal (5)**: Tongue to hard palate (SH, CH, Y sounds)
- **Velar (6)**: Tongue to soft palate (K, G, NG sounds)
- **Glottal (7)**: Throat sounds (H sounds)
- **Open Vowel (10)**: Wide open mouth (A, E sounds)
- **Mid Vowel (11)**: Medium mouth opening (E, ER sounds)
- **Close Front (12)**: Almost closed, tongue forward (I sounds)
- **Close Mid (13)**: Almost closed, tongue mid (O sounds)
- **Close Back (14)**: Almost closed, tongue back (U, O, W sounds)

## 📁 Project Structure

```
realtime-avatar-chat/
├── app.py                 # Main Flask application
├── ai_core.py            # AI integration (Gemini)
├── voice_utils.py        # Text-to-speech and viseme generation
├── viseme_utils.py       # Viseme mapping and timing logic
├── database.py           # SQLite database operations
├── forms.py              # Flask-WTF form definitions
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── static/
│   ├── js/
│   │   └── chat.js      # Frontend JavaScript with viseme sync
│   └── viseme_test_*.jpg # Viseme avatar images
├── templates/
│   ├── base.html        # Base template
│   ├── chat.html        # Main chat interface
│   ├── index.html       # Landing page
│   └── login.html       # Login form
└── README.md            # This file
```

## 🎮 Usage

### Basic Chat
1. Enter any username on the login page
2. Type messages in the chat input
3. Watch the avatar respond with synchronized lip movements

### Voice Features
1. Click the microphone button to start voice input
2. Speak your message
3. The AI will respond with voice and lip sync

### Controls
- **🔊 Voice Toggle**: Enable/disable voice output
- **🎤 Microphone**: Start/stop voice input
- **⛶ Fullscreen**: Toggle fullscreen mode

## 🛠️ Development

### Adding New Visemes
1. Add new viseme images to the `static/` directory
2. Update the `VISEME_MAPPING` in `viseme_utils.py`
3. Add image paths to the `viseme_images` dictionary

### Customizing Avatar
- Replace viseme images in the `static/` directory
- Update image paths in `viseme_utils.py`
- Modify CSS in templates for different styling

### Extending AI Capabilities
- Modify prompts in `ai_core.py`
- Add new conversation features
- Integrate additional AI models

## 🐛 Troubleshooting

### Common Issues

1. **"No module named 'flask'"**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`

2. **"API key not configured"**
   - Check your `.env` file
   - Verify API keys are correct

3. **Voice not working**
   - Check ElevenLabs API key
   - Ensure microphone permissions are granted

4. **Viseme images not loading**
   - Check file paths in `static/` directory
   - Verify image files exist and are accessible

### Debug Mode
Enable debug mode by setting `DEBUG=True` in your `.env` file for detailed error messages.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- **Google Gemini**: AI conversation capabilities
- **ElevenLabs**: High-quality text-to-speech
- **Flask**: Web framework
- **Socket.IO**: Real-time communication
- **Viseme Standards**: Based on Oculus VR lip sync standards

## 📞 Support

If you encounter any issues or have questions:
1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed information

---

**Made with ❤️ for immersive AI conversations**