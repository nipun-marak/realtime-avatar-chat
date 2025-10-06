// Global variables
let isVoiceEnabled = window.sessionData?.voiceEnabled ?? true;
let isFullscreen = window.sessionData?.fullscreen ?? false;
let isRecording = false;
let currentAudio = null;
let recognition = null;
let socket = null;

// Viseme lip sync variables
let currentVisemeFrames = [];
let visemeInterval = null;
let visemeStartTime = 0;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    initializeSpeechRecognition();
    initializeEventListeners();
    initializeAvatar();
});

// Socket.IO initialization
function initializeSocket() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to server');
    });
    
    socket.on('avatar_state_changed', (data) => {
        updateAvatarState(data.state, data.status_label);
    });
    
    socket.on('message_received', (data) => {
        appendMessage(data.message, data.sender);
    });
    
    socket.on('audio_ready', (data) => {
        playAudio(data.audio);
    });
    
    socket.on('voice_toggled', (data) => {
        updateVoiceToggle(data);
    });
    
    socket.on('fullscreen_toggled', (data) => {
        updateFullscreenState(data);
    });
}

// Avatar state management
async function setAvatarState(state) {
    try {
        const response = await fetch('/api/avatar_state', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ state: state })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            updateAvatarState(data.state, data.status_label);
            socket.emit('avatar_state_changed', data);
        }
    } catch (error) {
        console.error('Error setting avatar state:', error);
    }
}

function updateAvatarState(state, statusLabel) {
    const avatarContainer = document.getElementById('avatar-container');
    const statusElement = document.getElementById('avatar-status-label');
    const avatarMouth = document.getElementById('avatar-mouth');
    
    if (avatarContainer) {
        avatarContainer.className = `avatar-container ${state}`;
    }
    
    if (statusElement) {
        statusElement.textContent = statusLabel;
    }
    
    // Handle mouth animation based on state
    if (avatarMouth) {
        if (state === 'speaking') {
            // Keep mouth in neutral position when speaking (viseme sync will handle movement)
            avatarMouth.className = 'mouth-neutral';
        } else {
            // Close mouth when not speaking
            avatarMouth.className = 'mouth-closed';
        }
    }
}

// Message handling
function appendMessage(text, sender) {
    const chatHistory = document.getElementById('chat-history');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender + '-message');
    messageDiv.textContent = text;
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Audio handling
function stopCurrentAudio() {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
    }
    stopVisemeSync();
}

// Viseme lip sync functions
function startVisemeSync(visemeFrames) {
    stopVisemeSync();
    
    if (!visemeFrames || visemeFrames.length === 0) {
        return;
    }
    
    currentVisemeFrames = visemeFrames;
    visemeStartTime = Date.now();
    
    // Update avatar image immediately with first viseme
    updateAvatarViseme(visemeFrames[0]);
    
    // Set up interval to update visemes based on timing
    visemeInterval = setInterval(updateVisemeFromTime, 50); // Update every 50ms
}

function stopVisemeSync() {
    if (visemeInterval) {
        clearInterval(visemeInterval);
        visemeInterval = null;
    }
    currentVisemeFrames = [];
    visemeStartTime = 0;
    
    // Reset to default avatar image
    const avatarImg = document.getElementById('secondary-avatar');
    if (avatarImg) {
        avatarImg.src = '/static/Avatar.png';
    }
}

function updateVisemeFromTime() {
    if (currentVisemeFrames.length === 0) {
        stopVisemeSync();
        return;
    }
    
    const currentTime = (Date.now() - visemeStartTime) / 1000; // Convert to seconds
    const currentFrame = getCurrentVisemeFrame(currentTime);
    
    if (currentFrame) {
        updateAvatarViseme(currentFrame);
    }
}

function getCurrentVisemeFrame(currentTime) {
    for (const frame of currentVisemeFrames) {
        if (currentTime >= frame.start_time && currentTime < frame.start_time + frame.duration) {
            return frame;
        }
    }
    
    // If we're past all frames, return the last one or null
    if (currentTime >= currentVisemeFrames[currentVisemeFrames.length - 1].start_time + 
        currentVisemeFrames[currentVisemeFrames.length - 1].duration) {
        return null;
    }
    
    return currentVisemeFrames[0]; // Default to first frame
}

function updateAvatarViseme(frame) {
    const avatarImg = document.getElementById('secondary-avatar');
    const avatarMouth = document.getElementById('avatar-mouth');
    
    if (avatarImg && frame) {
        avatarImg.src = frame.image_path;
    }
    
    // Update mouth shape based on viseme
    if (avatarMouth && frame) {
        updateMouthShape(frame.viseme_id, frame.viseme_name);
    }
}

function updateMouthShape(visemeId, visemeName) {
    const avatarMouth = document.getElementById('avatar-mouth');
    
    if (!avatarMouth) return;
    
    // Apply viseme-specific mouth shapes
    switch(visemeId) {
        case 0: // Silence
            avatarMouth.className = 'mouth-closed';
            break;
        case 1: // Bilabial (p, b, m) - lips together
            avatarMouth.className = 'mouth-closed';
            break;
        case 2: // Labiodental (f, v) - lip to teeth
            avatarMouth.className = 'mouth-narrow';
            break;
        case 3: // Dental (th) - tongue between teeth
            avatarMouth.className = 'mouth-narrow';
            break;
        case 4: // Alveolar (t, d, n, s, z, l)
            avatarMouth.className = 'mouth-narrow';
            break;
        case 10: // Open vowel (a, aa, ae, ah) - mouth wide open
            avatarMouth.className = 'mouth-wide-e';
            break;
        case 11: // Mid vowel (e, eh, er)
            avatarMouth.className = 'mouth-neutral';
            break;
        case 12: // Close-front vowel (i, ih, iy) - mouth almost closed
            avatarMouth.className = 'mouth-closed';
            break;
        case 13: // Close-mid vowel (o, ow, oy)
            avatarMouth.className = 'mouth-open-o';
            break;
        case 14: // Close-back vowel (u, uh, uw) - rounded lips
            avatarMouth.className = 'mouth-open-o';
            break;
        default:
            // Default neutral position
            avatarMouth.className = 'mouth-neutral';
            break;
    }
}

async function playAudio(audioData) {
    stopCurrentAudio();
    if (!isVoiceEnabled) {
        await setAvatarState('idle');
        return;
    }
    
    // Handle both old format (base64 string) and new format (object with viseme data)
    let base64Data, visemeFrames;
    
    if (typeof audioData === 'string') {
        base64Data = audioData;
    } else if (audioData && audioData.audio) {
        base64Data = audioData.audio;
        visemeFrames = audioData.viseme_frames;
    } else {
        await setAvatarState('idle');
        return;
    }
    
    if (!base64Data) {
        await setAvatarState('idle');
        return;
    }
    
    await setAvatarState('speaking');
    
    // Start viseme sync if available
    if (visemeFrames && visemeFrames.length > 0) {
        startVisemeSync(visemeFrames);
    }
    
    const audioSrc = "data:audio/mpeg;base64," + base64Data;
    currentAudio = new Audio(audioSrc);
    currentAudio.play().catch(e => {
        console.error("Audio play failed:", e);
        setAvatarState('idle');
        stopVisemeSync();
    });
    currentAudio.onended = async () => {
        await setAvatarState('idle');
        stopVisemeSync();
    };
}

// Form handling
function initializeEventListeners() {
    const chatForm = document.getElementById('chat-form');
    const toggleVoiceBtn = document.getElementById('toggle-voice-btn');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const userInput = document.getElementById('user-input');
    
    if (chatForm) {
        chatForm.addEventListener('submit', handleFormSubmit);
    }
    
    if (toggleVoiceBtn) {
        toggleVoiceBtn.addEventListener('click', handleVoiceToggle);
    }
    
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', handleFullscreenToggle);
    }
    
    if (userInput) {
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleFormSubmit(e);
            }
        });
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const micBtn = document.getElementById('mic-btn');
    const statusIndicator = document.getElementById('status-indicator');
    
    const message = userInput.value.trim();
    if (!message) return;
    
    await appendMessage(message, 'user');
    userInput.value = '';
    await setAvatarState('thinking');
    statusIndicator.textContent = "Companion is thinking...";
    sendButton.disabled = true;
    micBtn.disabled = true;
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            await appendMessage(data.message, 'bot');
            
            // Add emotional expression based on bot's response
            addEmotionalExpression(data.message);
            
            // Pass complete audio data including viseme frames
            const audioData = {
                audio: data.audio,
                viseme_frames: data.viseme_frames,
                estimated_duration: data.estimated_duration
            };
            await playAudio(audioData);
            // Removed duplicate socket emission that was causing double messages
        } else {
            await appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        await appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
    } finally {
        statusIndicator.textContent = '';
        sendButton.disabled = false;
        micBtn.disabled = false;
        userInput.focus();
    }
}

// Speech recognition setup
function initializeSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        try {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            const micBtn = document.getElementById('mic-btn');
            if (micBtn) {
                micBtn.addEventListener('click', handleMicClick);
            }

            recognition.onstart = async () => {
                isRecording = true;
                micBtn.classList.add('recording');
                await setAvatarState('listening');
                document.getElementById('status-indicator').textContent = "Listening... (click mic to stop)";
            };

            recognition.onresult = async (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById('user-input').value = transcript;
                
                // Submit the form with the transcript
                const form = document.getElementById('chat-form');
                if (form) {
                    form.dispatchEvent(new Event('submit'));
                }
            };

            recognition.onerror = (event) => {
                isRecording = false;
                micBtn.classList.remove('recording');
                console.error("Speech recognition error:", event.error);
                setAvatarState('idle');
                
                let errorMessage = "";
                switch(event.error) {
                    case 'not-allowed':
                    case 'permission-denied':
                        errorMessage = "⚠️ Microphone access denied. Please allow microphone access in your browser settings.";
                        break;
                    case 'no-speech':
                        errorMessage = "No speech detected. Please try again.";
                        break;
                    case 'audio-capture':
                        errorMessage = "No microphone found. Please check your device.";
                        break;
                    case 'network':
                        errorMessage = "Network error. Please check your connection.";
                        break;
                    case 'aborted':
                        break;
                    default:
                        errorMessage = `Microphone error: ${event.error}`;
                }

                if (errorMessage) {
                    document.getElementById('status-indicator').textContent = errorMessage;
                    setTimeout(() => { 
                        document.getElementById('status-indicator').textContent = ''; 
                    }, 5000);
                }
            };

            recognition.onend = () => {
                isRecording = false;
                micBtn.classList.remove('recording');
                const avatarContainer = document.getElementById('avatar-container');
                if (avatarContainer && avatarContainer.className.includes('listening')) {
                    setAvatarState('idle');
                    const statusIndicator = document.getElementById('status-indicator');
                    if (statusIndicator.textContent === "Listening... (click mic to stop)") {
                        statusIndicator.textContent = '';
                    }
                }
            };

        } catch(e) {
            console.error("Speech recognition initialization error:", e);
            const micBtn = document.getElementById('mic-btn');
            if (micBtn) {
                micBtn.disabled = true;
                micBtn.style.color = '#ccc';
                micBtn.title = 'Voice recognition initialization failed.';
            }
        }
    } else {
        const micBtn = document.getElementById('mic-btn');
        if (micBtn) {
            micBtn.disabled = true;
            micBtn.style.color = '#ccc';
            micBtn.title = 'Voice recognition not supported. Please use Chrome or Edge.';
        }
    }
}

async function handleMicClick() {
    if (isRecording) {
        recognition.stop();
        isRecording = false;
        document.getElementById('mic-btn').classList.remove('recording');
        await setAvatarState('idle');
        document.getElementById('status-indicator').textContent = '';
        return;
    }

    stopCurrentAudio();
    try {
        await setAvatarState('listening');
        recognition.start();
        isRecording = true;
        document.getElementById('mic-btn').classList.add('recording');
    } catch(e) {
        console.error("Recognition start error:", e);
        document.getElementById('status-indicator').textContent = "Please wait, microphone is busy...";
        setTimeout(() => { 
            document.getElementById('status-indicator').textContent = ''; 
        }, 2000);
    }
}

// Voice toggle
async function handleVoiceToggle() {
    isVoiceEnabled = !isVoiceEnabled;
    
    try {
        const response = await fetch('/api/toggle_voice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ enabled: isVoiceEnabled })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            updateVoiceToggle(data);
            socket.emit('voice_toggled', data);
        }
    } catch (error) {
        console.error('Error toggling voice:', error);
    }
}

function updateVoiceToggle(data) {
    isVoiceEnabled = data.enabled;
    document.getElementById('toggle-voice-btn').textContent = data.icon;
    
    if (!isVoiceEnabled) {
        stopCurrentAudio();
        setAvatarState('idle');
        stopVisemeSync();
    }
}

// Fullscreen functionality
function updateFullscreenState(data) {
    isFullscreen = data.enabled;
    updateFullscreenUI();
}

function updateFullscreenUI() {
    const mainLayout = document.getElementById('main-layout');
    
    if (isFullscreen) {
        const overlay = document.createElement('div');
        overlay.id = 'fullscreen-overlay';
        overlay.classList.add('fullscreen-overlay');
        mainLayout.classList.add('fullscreen-chat-layout');
        overlay.appendChild(mainLayout);
        document.body.appendChild(overlay);
    } else {
        const overlay = document.getElementById('fullscreen-overlay');
        if (overlay) {
            document.body.appendChild(mainLayout);
            document.body.removeChild(overlay);
            mainLayout.classList.remove('fullscreen-chat-layout');
        }
    }
}

async function handleFullscreenToggle() {
    isFullscreen = !isFullscreen;
    
    try {
        const response = await fetch('/api/fullscreen/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ fullscreen: isFullscreen })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            updateFullscreenUI();
            socket.emit('fullscreen_toggled', data);
        }
    } catch (error) {
        console.error('Error toggling fullscreen:', error);
    }
    
    document.getElementById('user-input').focus();
}

// Initialize avatar state
function initializeAvatar() {
    const avatarState = window.sessionData?.avatarState || 'idle';
    setAvatarState(avatarState);
    
    // Initialize mouth to closed state
    const avatarMouth = document.getElementById('avatar-mouth');
    if (avatarMouth) {
        avatarMouth.className = 'mouth-closed';
    }
}

// Add emotional expressions based on message content
function addEmotionalExpression(message) {
    const avatarMouth = document.getElementById('avatar-mouth');
    const avatarHead = document.querySelector('.avatar-head');
    
    if (!avatarMouth || !avatarHead) return;
    
    // Simple emotion detection based on keywords
    const positiveWords = ['happy', 'good', 'great', 'excellent', 'wonderful', 'amazing', 'love', 'like', 'thanks', 'thank you', 'welcome'];
    const negativeWords = ['sad', 'bad', 'terrible', 'awful', 'hate', 'angry', 'upset', 'worried', 'sorry'];
    const questionWords = ['what', 'how', 'why', 'when', 'where', 'who', '?'];
    
    const isPositive = positiveWords.some(word => message.toLowerCase().includes(word));
    const isNegative = negativeWords.some(word => message.toLowerCase().includes(word));
    const isQuestion = questionWords.some(word => message.toLowerCase().includes(word));
    
    if (isPositive) {
        // Happy expression - smile
        avatarMouth.className = 'mouth-smile';
        setTimeout(() => {
            avatarMouth.className = 'mouth-closed';
        }, 2000);
    } else if (isNegative) {
        // Concerned expression - slight frown
        avatarMouth.className = 'mouth-frown';
        setTimeout(() => {
            avatarMouth.className = 'mouth-closed';
        }, 2000);
    } else if (isQuestion) {
        // Questioning expression - neutral with slight opening
        avatarMouth.className = 'mouth-neutral';
        setTimeout(() => {
            avatarMouth.className = 'mouth-closed';
        }, 1500);
    }
}
