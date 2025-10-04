"""
Viseme-based lip sync utilities for real-time avatar chat.
Handles phoneme to viseme mapping and timing calculations.
"""

import re
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class VisemeFrame:
    """Represents a single viseme frame with timing information."""
    viseme_id: int
    viseme_name: str
    image_path: str
    start_time: float
    duration: float
    intensity: float = 1.0

class VisemeMapper:
    """Maps phonemes to visemes and manages timing for lip sync."""
    
    # Standard viseme mapping based on Oculus VR lip sync standard
    VISEME_MAPPING = {
        # Silence/Neutral
        0: {"name": "Silence", "phonemes": ["sil", "pau", "sp"]},
        
        # Bilabial (lips together)
        1: {"name": "Bilabial_pbm", "phonemes": ["p", "b", "m", "em", "en"]},
        
        # Labiodental (lip to teeth)
        2: {"name": "Labiodental_fv", "phonemes": ["f", "v"]},
        
        # Linguolabial
        3: {"name": "Linguolabial", "phonemes": ["th"]},
        
        # Alveolar (tongue to roof)
        4: {"name": "Alveolar_tdn", "phonemes": ["t", "d", "n", "s", "z", "l", "r"]},
        
        # Palatal
        5: {"name": "Palatal", "phonemes": ["sh", "zh", "ch", "jh", "y"]},
        
        # Velar
        6: {"name": "Velar", "phonemes": ["k", "g", "ng"]},
        
        # Glottal
        7: {"name": "Glottal", "phonemes": ["h", "hh"]},
        
        # Open vowel (mouth open wide)
        10: {"name": "Open_vowel_a", "phonemes": ["a", "aa", "ae", "ah"]},
        
        # Mid vowel
        11: {"name": "Mid_vowel_e", "phonemes": ["e", "eh", "er", "ax", "axr"]},
        
        # Close-front vowel (mouth almost closed, tongue forward)
        12: {"name": "Close-front_i", "phonemes": ["i", "ih", "iy"]},
        
        # Close-mid vowel
        13: {"name": "Close-mid_o", "phonemes": ["o", "ow", "oy"]},
        
        # Close-back vowel (mouth almost closed, tongue back)
        14: {"name": "Close-back_u", "phonemes": ["u", "uh", "uw", "w"]},
    }
    
    # Duration estimates for different phoneme types (in seconds)
    PHONEME_DURATIONS = {
        "vowels": 0.15,      # Vowels are typically longer
        "consonants": 0.08,  # Consonants are typically shorter
        "silence": 0.1,      # Brief pause between words
        "default": 0.12      # Default duration
    }
    
    def __init__(self):
        """Initialize the viseme mapper."""
        self.viseme_images = {
            0: "/static/viseme_test_00_Silence.jpg",
            1: "/static/viseme_test_01_Bilabial_pbm.jpg",
            4: "/static/viseme_test_04_Alveolar_tdn.jpg",
            10: "/static/viseme_test_10_Open_vowel_a.jpg",
            14: "/static/viseme_test_14_Close-back_u.jpg",
            12: "/static/viseme_test_12_Close-front_i.jpg",
        }
        
        # Create reverse mapping for faster lookup
        self.phoneme_to_viseme = {}
        for viseme_id, data in self.VISEME_MAPPING.items():
            for phoneme in data["phonemes"]:
                self.phoneme_to_viseme[phoneme] = viseme_id
    
    def text_to_phonemes(self, text: str) -> List[str]:
        """
        Convert text to phonemes using simple rule-based approach.
        In a production system, you would use a proper phonetic transcription service.
        """
        # Simple rule-based phoneme mapping for demonstration
        text = text.lower()
        phonemes = []
        
        # Common word mappings
        word_phonemes = {
            "hello": ["h", "eh", "l", "ow"],
            "hi": ["h", "ay"],
            "how": ["h", "aw"],
            "are": ["aa", "r"],
            "you": ["y", "uw"],
            "doing": ["d", "uw", "ih", "ng"],
            "today": ["t", "uh", "d", "ey"],
            "what": ["w", "ah", "t"],
            "is": ["ih", "z"],
            "your": ["y", "er"],
            "name": ["n", "ey", "m"],
            "thank": ["th", "ae", "ng", "k"],
            "thanks": ["th", "ae", "ng", "k", "s"],
            "good": ["g", "uh", "d"],
            "morning": ["m", "er", "n", "ih", "ng"],
            "afternoon": ["ae", "f", "t", "er", "n", "uw", "n"],
            "evening": ["iy", "v", "n", "ih", "ng"],
            "night": ["n", "ay", "t"],
            "bye": ["b", "ay"],
            "goodbye": ["g", "uh", "d", "b", "ay"],
            "please": ["p", "l", "iy", "z"],
            "sorry": ["s", "aa", "r", "iy"],
            "yes": ["y", "eh", "s"],
            "no": ["n", "ow"],
            "okay": ["ow", "k", "ey"],
            "ok": ["ow", "k"],
            "sure": ["sh", "er"],
            "maybe": ["m", "ey", "b", "iy"],
            "think": ["th", "ih", "ng", "k"],
            "know": ["n", "ow"],
            "see": ["s", "iy"],
            "look": ["l", "uh", "k"],
            "hear": ["h", "ih", "r"],
            "feel": ["f", "iy", "l"],
            "want": ["w", "ah", "n", "t"],
            "need": ["n", "iy", "d"],
            "like": ["l", "ay", "k"],
            "love": ["l", "ah", "v"],
            "happy": ["h", "ae", "p", "iy"],
            "sad": ["s", "ae", "d"],
            "angry": ["ae", "ng", "g", "r", "iy"],
            "tired": ["t", "ay", "er", "d"],
            "excited": ["ih", "k", "s", "ay", "t", "ih", "d"],
            "nervous": ["n", "er", "v", "ah", "s"],
            "worried": ["w", "er", "iy", "d"],
            "calm": ["k", "aa", "m"],
            "relaxed": ["r", "ih", "l", "ae", "k", "s", "t"],
        }
        
        # Split text into words
        words = re.findall(r'\b\w+\b', text)
        
        for word in words:
            if word in word_phonemes:
                phonemes.extend(word_phonemes[word])
            else:
                # Simple letter-to-phoneme mapping for unknown words
                for char in word:
                    if char in "aeiou":
                        # Vowels
                        vowel_map = {
                            "a": "ae", "e": "eh", "i": "ih", 
                            "o": "ah", "u": "ah"
                        }
                        phonemes.append(vowel_map.get(char, "ah"))
                    elif char in "bcdfghjklmnpqrstvwxyz":
                        # Consonants
                        consonant_map = {
                            "b": "b", "c": "k", "d": "d", "f": "f", "g": "g",
                            "h": "h", "j": "jh", "k": "k", "l": "l", "m": "m",
                            "n": "n", "p": "p", "q": "k", "r": "r", "s": "s",
                            "t": "t", "v": "v", "w": "w", "x": "k", "y": "y", "z": "z"
                        }
                        phonemes.append(consonant_map.get(char, "sil"))
            
            # Add brief silence between words
            phonemes.append("sil")
        
        # Remove trailing silence
        if phonemes and phonemes[-1] == "sil":
            phonemes.pop()
            
        return phonemes
    
    def phonemes_to_visemes(self, phonemes: List[str]) -> List[VisemeFrame]:
        """
        Convert phonemes to viseme frames with timing.
        """
        viseme_frames = []
        current_time = 0.0
        
        for i, phoneme in enumerate(phonemes):
            # Get viseme ID for this phoneme
            viseme_id = self.phoneme_to_viseme.get(phoneme, 0)  # Default to silence
            
            # Determine duration based on phoneme type
            if phoneme in ["a", "aa", "ae", "ah", "e", "eh", "i", "ih", "o", "ow", "u", "uh"]:
                duration = self.PHONEME_DURATIONS["vowels"]
            elif phoneme == "sil":
                duration = self.PHONEME_DURATIONS["silence"]
            else:
                duration = self.PHONEME_DURATIONS["consonants"]
            
            # Create viseme frame
            viseme_name = self.VISEME_MAPPING[viseme_id]["name"]
            image_path = self.viseme_images.get(viseme_id, self.viseme_images[0])  # Default to silence
            
            frame = VisemeFrame(
                viseme_id=viseme_id,
                viseme_name=viseme_name,
                image_path=image_path,
                start_time=current_time,
                duration=duration,
                intensity=1.0
            )
            
            viseme_frames.append(frame)
            current_time += duration
        
        return viseme_frames
    
    def text_to_visemes(self, text: str) -> List[VisemeFrame]:
        """
        Convert text directly to viseme frames.
        """
        phonemes = self.text_to_phonemes(text)
        return self.phonemes_to_visemes(phonemes)
    
    def get_viseme_for_time(self, viseme_frames: List[VisemeFrame], current_time: float) -> Optional[VisemeFrame]:
        """
        Get the current viseme frame for a given time.
        """
        for frame in viseme_frames:
            if frame.start_time <= current_time < frame.start_time + frame.duration:
                return frame
        return None
    
    def create_viseme_timeline(self, text: str, total_duration: float) -> List[VisemeFrame]:
        """
        Create a viseme timeline for the given text and total duration.
        Scales the timing to match the audio duration.
        """
        viseme_frames = self.text_to_visemes(text)
        
        if not viseme_frames:
            return []
        
        # Calculate total viseme duration
        viseme_duration = sum(frame.duration for frame in viseme_frames)
        
        # Scale factor to match audio duration
        scale_factor = total_duration / viseme_duration if viseme_duration > 0 else 1.0
        
        # Scale all timing
        for frame in viseme_frames:
            frame.duration *= scale_factor
        
        # Update start times
        current_time = 0.0
        for frame in viseme_frames:
            frame.start_time = current_time
            current_time += frame.duration
        
        return viseme_frames

# Global viseme mapper instance
viseme_mapper = VisemeMapper()
