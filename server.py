from flask import Flask, request, jsonify
import os
import shutil
import requests
from datetime import datetime
from PIL import Image
import uuid
import cv2
import numpy as np
from inference_sdk import InferenceHTTPClient
import whisper
from ultralytics import YOLO
import re
from gtts import gTTS
import subprocess
from io import BytesIO

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize models
WHISPER_MODEL = whisper.load_model("turbo") 
CLASSIFICATION_MODEL = YOLO("Final_2.pt")
CURRENCY_MODEL = None

# Initialize Inference Client
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key="VJuz28pn9I7Ovb5DkYTt"
)

# Database API configuration
DATABASE_API_URL = "http://127.0.0.1:5000/get_item_position"

# Class labels for products - updated with all possible classes


# Global mode variable
current_mode = 0

def clean_text(text):
    """Normalize text for comparison by removing punctuation and extra spaces"""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text)     # Collapse multiple spaces
    return text

def play_audio(file_path):
    """Play an audio file using a system command."""
    try:
        subprocess.run(["ffplay", "-nodisp", "-autoexit", file_path], check=True)
    except Exception as e:
        print(f"Failed to play audio: {str(e)}")

def send_to_database(item_name):
    """Send identified product to database API with TTS response"""
    try:
        payload = {"item_name": clean_text(item_name)}
        print(f"\nSending product to database: {item_name}")
        
        response = requests.post(DATABASE_API_URL, json=payload)
        response_data = response.json()
        
        if response.status_code == 200:
            if "error" in response_data:
                response_text = f"Could not find {item_name} in the database."
            else:
                position = response_data.get('position_in_row', 'unknown')
                row = response_data.get('row_from_top', 'unknown')
                response_text = f"{item_name} is located at position {position} in row {row}."
        else:
            error_msg = response_data.get('error', 'an unknown error occurred')
            response_text = f"Error. {error_msg} while looking up {item_name}."
        
        print(f"\nDatabase response: {response_text}")
        
        tts = gTTS(text=response_text, lang='en')
        tts.save("response.mp3")
        play_audio("response.mp3")
        os.remove("response.mp3")
        
        return "error" not in response_data
            
    except Exception as e:
        error_text = f"Failed to connect to database service. Error: {str(e)}"
        print(f"\nDatabase response: {error_text}")
        
        tts = gTTS(text=error_text, lang='en')
        tts.save("error.mp3")
        play_audio("error.mp3")
        os.remove("error.mp3")
        
        return False
    
def clear_upload_folder():
    """Clears all files in the upload folder"""
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
        print("Upload folder cleared successfully")
        return True
    except Exception as e:
        print(f"Error clearing upload folder: {str(e)}")
        return False

def get_top_prediction(image_path):
    """Get the top prediction from YOLO model with confidence"""
    try:
        results = CLASSIFICATION_MODEL(image_path)
        
        if not results or len(results) == 0:
            print("No results returned from model")
            return None
            
        # Get the first result (assuming single image input)
        result = results[0]
        
        if not hasattr(result, 'probs') or result.probs is None:
            print("No probabilities in results")
            return None
            
        top1_idx = int(result.probs.top1)
        confidence = float(result.probs.top1conf)
        
        # Use model's native class names instead of CLASS_LABELS
        class_name = result.names[top1_idx]
        clean_name = clean_text(class_name)
        
        print(f"Detected: {class_name} (Confidence: {confidence:.2f})")
        return {
            'class': class_name,
            'confidence': confidence,
            'clean_class': clean_name
        }
        
    except Exception as e:
        print(f"Error getting prediction: {str(e)}")
        return None

def process_currency(image_path):
    """Process image through currency detection model"""
    global CURRENCY_MODEL
    try:
        if CURRENCY_MODEL is None:
            CURRENCY_MODEL = YOLO("currency.pt")
            
        results = CURRENCY_MODEL(image_path)
        
        best_currency = None
        highest_confidence = 0
        
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)
                currency = result.names[class_id]
                
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_currency = currency
        
        if best_currency:
            response_text = f"You are holding {best_currency} in your hand."
        else:
            response_text = "No currency detected in the image."
        
        tts = gTTS(text=response_text, lang='en')
        tts.save("currency_response.mp3")
        play_audio("currency_response.mp3")
        os.remove("currency_response.mp3")
        
        return True
        
    except Exception as e:
        print(f"Error processing currency: {str(e)}")
        return False

def process_image_with_model(image_path):
    """Process image through detection model and save cropped objects"""
    try:
        result = CLIENT.infer(image_path, model_id="sku-110k/2")
        image = Image.open(image_path)
        detections = result.get("predictions", [])
        print(f"Found {len(detections)} objects in image")
        
        cropped_images = []
        for detection in detections:
            x, y = detection['x'], detection['y']
            width, height = detection['width'], detection['height']
            left, top = x - width/2, y - height/2
            right, bottom = x + width/2, y + height/2
            
            cropped_image = image.crop((left, top, right, bottom))
            random_name = uuid.uuid4().hex
            cropped_path = os.path.join(UPLOAD_FOLDER, f'cropped_object_{random_name}.jpg')
            cropped_image.save(cropped_path)
            cropped_images.append(cropped_path)
            print(f"Saved cropped object to {cropped_path}")
            
        return cropped_images
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None

def transcribe_audio(audio_path):
    """Transcribe audio using Whisper model and clean the text"""
    try:
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"The file {audio_path} does not exist.")
        
        result = WHISPER_MODEL.transcribe(audio_path, language='en')
        raw_transcription = result["text"]
        transcription = clean_text(raw_transcription)
        print(f"Audio transcription (raw): {raw_transcription}")
        print(f"Audio transcription (cleaned): {transcription}")
        return transcription
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        return None

@app.route('/uploadImage', methods=['POST'])
def upload_image():
    try:
        clear_upload_folder()
        file_data = request.data
        
        if not file_data:
            return jsonify({"error": "No file data received"}), 400

        filename = f"image_.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            img = Image.open(BytesIO(file_data))
            img = img.rotate(90 * 2, expand=True)
            with open(filepath, 'wb') as f:
                img.save(f, format='JPEG')
            print(f"Received and rotated image: {filename}")
        except Exception as img_error:
            with open(filepath, 'wb') as f:
                f.write(file_data)
            print(f"Received unrotated image: {filename}")
        
        if current_mode == 0:
            print("Processing image through product detection model...")
            cropped_images = process_image_with_model(filepath)
            if not cropped_images:
                return jsonify({"warning": "Image saved but processing failed"}), 200
            
            return jsonify({
                "message": "Image uploaded successfully (product mode)",
                "filename": filename,
                "cropped_images": cropped_images
            }), 200
        else:
            print("Processing image through currency detection model...")
            success = process_currency(filepath)
            if success:
                return jsonify({
                    "message": "Currency detection completed",
                    "filename": filename
                }), 200
            else:
                return jsonify({"error": "Currency detection failed"}), 500
        
    except Exception as e:
        print(f"Image upload error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/uploadAudio', methods=['POST'])
def upload_audio():
    try:
        if current_mode == 1:
            print("Audio ignored (currency detection mode active)")
            return jsonify({"message": "Audio processing disabled in currency mode"}), 200
            
        file_data = request.data
        
        if not file_data:
            return jsonify({"error": "No file data received"}), 400
            
        filename = f"audio_.wav"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(file_data)
        print(f"Received audio: {filename}")
        
        transcription = transcribe_audio(filepath)
        if not transcription:
            tts = gTTS(text="Could not understand audio", lang='en')
            tts.save("error.mp3")
            play_audio("error.mp3")
            os.remove("error.mp3")
            return jsonify({"error": "Transcription failed"}), 400
        
        cropped_images = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) 
                         if f.startswith('cropped_object_') and f.endswith('.jpg')]
        
        for img_path in cropped_images:
            prediction = get_top_prediction(img_path)
            if not prediction:
                continue
                
            print(f"Checking if '{prediction['clean_class']}' matches '{transcription}'")
            
            # More flexible matching - check if either:
            # 1. The class name is in the transcription, or
            # 2. The transcription is in the class name
            if (prediction['clean_class'] in transcription or 
                transcription in prediction['clean_class']):
                
                print(f"MATCH FOUND: {prediction['class']}")
                send_to_database(prediction['class'])
                return jsonify({
                    "message": "PRODUCT IDENTIFIED",
                    "product": prediction['class'],
                    "confidence": prediction['confidence']
                }), 200
        
        print("NO PRODUCT MATCH FOUND")
        tts = gTTS(text="  No product match found", lang='en')
        tts.save("no_match.mp3")
        play_audio("no_match.mp3")
        os.remove("no_match.mp3")
        
        return jsonify({"message": "NO PRODUCT MATCH FOUND"}), 200
        
    except Exception as e:
        print(f"Audio upload error: {str(e)}")
        tts = gTTS(text="An error occurred while processing", lang='en')
        tts.save("error.mp3")
        play_audio("error.mp3")
        os.remove("error.mp3")
        return jsonify({"error": str(e)}), 500
    
@app.route('/uploadMode', methods=['POST'])
def upload_mode():
    global current_mode, CURRENCY_MODEL
    try:
        mode = request.data.decode('utf-8')
        if mode not in ['0', '1']:
            tts = gTTS(text="Invalid mode selection", lang='en')
            tts.save("mode_error.mp3")
            play_audio("mode_error.mp3")
            os.remove("mode_error.mp3")
            return jsonify({"error": "Invalid mode value"}), 400
            
        new_mode = int(mode)
        mode_changed = (new_mode != current_mode)
        current_mode = new_mode
        
        if mode_changed:
            if current_mode == 0:
                tts_text = "Switched to product recognition mode."
            else:
                tts_text = "Switched to currency detection mode."
                if CURRENCY_MODEL is None:
                    try:
                        CURRENCY_MODEL = YOLO("currency.pt")
                        tts_text += " Currency model loaded successfully."
                    except Exception as e:
                        print(f"Failed to load currency model: {str(e)}")
            
            print(f"Mode updated to: {current_mode}")
            tts = gTTS(text=tts_text, lang='en')
            tts.save("mode_change.mp3")
            play_audio("mode_change.mp3")
            os.remove("mode_change.mp3")
        
        return jsonify({
            "message": "Mode updated successfully", 
            "mode": current_mode,
            "mode_changed": mode_changed
        }), 200
        
    except Exception as e:
        print(f"Error changing mode: {str(e)}")
        tts = gTTS(text="Error changing mode", lang='en')
        tts.save("mode_error.mp3")
        play_audio("mode_error.mp3")
        os.remove("mode_error.mp3")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, threaded=True, debug=True)