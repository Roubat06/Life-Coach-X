from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from flask_cors import CORS
import os
import json
import traceback
import logging
import uuid
import re
import io
import feedparser
import numpy as np
import soundfile as sf
from datetime import datetime
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY is not set!")
else:
    genai.configure(api_key=api_key)
    print("Gemini API key loaded")



def get_gemini_model_name():
    available_models = genai.list_models()
    models_list = [model.name for model in available_models]
    
    # Try to find "gemini-2.0" model (you can also be more specific with versioning like gemini-2.0-flash)
    gemini_2_0_model = next((m for m in models_list if "gemini-2.0" in m.lower()), None)
    
    if gemini_2_0_model:
        return gemini_2_0_model  # Return Gemini 2.0 model if found
    
    # Fallback to "flash" or "pro" models if Gemini 2.0 is not available
    flash_model = next((m for m in models_list if "flash" in m.lower()), None)
    if flash_model:
        return flash_model
    
    pro_model = next((m for m in models_list if "pro" in m.lower()), None)
    if pro_model:
        return pro_model
    
    # Final fallback (if no "flash" or "pro" models found)
    return "gemini-2.0-flash"  # You can replace this with a more general fallback if needed



app = Flask(__name__)
RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
    "https://feeds.feedburner.com/bodybuilding-exercises",
    "https://www.bodybuilding.com/rss/articles",
    "https://www.menshealth.com/rss/all.xml/",
    "https://www.shape.com/feeds/all/rss.xml"
]
CORS(app)  

@app.route('/')
def dashboard():
    return render_template('dashboard.html')
@app.route('/chatbot')
def chat_page():
    return render_template('chatbot.html') 
@app.route('/diet')
def diet_page():
    return render_template('diet.html')  
@app.route('/intake')
def intake_page():
    return render_template('intake.html')  
@app.route('/sound')
def sound_page():
    return render_template('sound.html') 
@app.route('/user_data')
def user_data_page():
    return render_template('user_data.html')
@app.route('/workout')
def workout_page():
    return render_template('workout.html') 
@app.route('/news')
def news():
    return render_template('news.html') 

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)




@app.route('/chat', methods=['POST'])
def chat_response():
    try:
        user_input = request.json.get("message", "")
        if not user_input:
            return jsonify({"error": "No user input provided"}), 400

        model_name = get_gemini_model_name()
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(user_input)
        return jsonify({"response": response.text})
    
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    







@app.route('/generate_diet_plan', methods=['POST'])
def generate_diet_plan():
    try:
        # Get user data from request
        user_data = request.json
        print(f"Received user data: {json.dumps(user_data, indent=2)}")
        
        # Validate required fields
        required_fields = ['name', 'age', 'gender', 'weight', 'height', 'activity_level', 'goal']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                error_msg = f'Missing required field: {field}'
                print(error_msg)
                return jsonify({'error': error_msg}), 400
        
        # Create prompt for Gemini model
        prompt = create_diet_plan_prompt(user_data)
        print(f"Generated prompt: {prompt}")
        
        # Generate diet plan using Gemini
        if not api_key:
            return jsonify({'error': 'API key not configured. Please check your .env file.'}), 500
        
        try:
            # Use the correct model name for Gemini 2.0 Flash
            # The model name might be "gemini-1.5-flash" or similar - fetch available models to verify
            model_name = get_gemini_model_name()
            print(f"Using Gemini model: {model_name}")

            
            model = genai.GenerativeModel(model_name)
            print(f"Making request to Gemini API using model: {model_name}")
            response = model.generate_content(prompt)
            print("Got response from Gemini API")
            
            # Return diet plan
            return jsonify({
                'diet_plan': response.text
            })
        except Exception as gemini_error:
            print(f"Gemini API error: {str(gemini_error)}")
            return jsonify({'error': f'Gemini API error: {str(gemini_error)}'}), 500
    
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error: {str(e)}")
        print(error_details)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

def create_diet_plan_prompt(user_data):
    # Extract user information
    name = user_data['name']
    age = user_data['age']
    gender = user_data['gender']
    weight = user_data['weight']
    height = user_data['height']
    activity_level = user_data['activity_level']
    goal = user_data['goal']
    dietary_restrictions = user_data.get('dietary_restrictions', [])
    allergies = user_data.get('allergies', '')
    preferences = user_data.get('preferences', '')
    
    # Calculate BMI
    bmi = weight / ((height / 100) ** 2)
    
    # Format the prompt for the Gemini model
    prompt = f"""
    Create a detailed 7-day personalized diet plan for {name}. Here's their information:
    
    - Age: {age}
    - Gender: {gender}
    - Weight: {weight} kg
    - Height: {height} cm
    - BMI: {bmi:.1f}
    - Activity Level: {activity_level}
    - Goal: {goal}
    - Dietary Restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
    - Allergies/Intolerances: {allergies if allergies else 'None'}
    - Food Preferences: {preferences if preferences else 'None'}
    
    The diet plan should include:
    1. A brief introduction explaining the approach and nutritional strategy based on their goal and activity level
    2. Estimated daily calorie target and macronutrient breakdown
    3. A 7-day meal plan with breakfast, lunch, dinner, and snacks
    4. Simple recipes or meal ideas that match their dietary restrictions and preferences
    5. General nutrition tips and hydration guidelines
    6. Foods to emphasize and foods to limit based on their goals
    
    Format the diet plan with clear sections, bullet points for meals, and emphasize important information.
    """
    
    return prompt








@app.route('/analyze', methods=['POST'])
def analyze_intake():
    try:
        logger.debug("Received request to /analyze")
        data = request.get_json()
        logger.debug(f"Received data: {data}")
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "No data provided"}), 400
            
        intake_text = data.get('intake', '')
        
        if not intake_text:
            logger.error("No intake text provided")
            return jsonify({"error": "No food intake provided"}), 400
        
        logger.debug(f"Processing intake: {intake_text}")
        
        # Prepare prompt for Gemini
        prompt = f"""
        Analyze the following food intake from a health perspective:
        
        {intake_text}
        
        Please provide a structured analysis with the following information:
        1. Calculate approximate total calories
        2. Break down the nutritional value of each meal
        3. Identify any potentially harmful ingredients or concerns
        4. Evaluate if this diet is healthy overall
        5. Provide specific recommendations for improvement if necessary
        
        Format the response as a JSON with the following structure:
        {{
            "total_calories": approximate number,
            "meals": {{
                "breakfast": {{
                    "calories": approximate number,
                    "nutrients": ["list of key nutrients"],
                    "harmful_elements": ["list of potentially harmful ingredients"]
                }},
                ... (same for other meals)
            }},
            "health_verdict": {{
                "overall": "overall assessment",
                "calorie_assessment": "calorie evaluation",
                "nutrient_assessment": "nutrition evaluation",
                "harmful_assessment": "evaluation of harmful elements"
            }},
            "recommendations": ["list of specific recommendations"]
        }}
        
        Note: If no specific meal types are mentioned, categorize everything under "unspecified" meal.
        Be accurate but if you don't have exact calorie information, provide reasonable estimates.
        """
        
        try:
            # Get response from Gemini
            logger.debug("Sending request to Gemini API")
            model_name = get_gemini_model_name()
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            logger.debug(f"Received response from Gemini: {response.text}")
            
            try:
                # Parse JSON response
                analysis_result = response.text
                
                # Clean up the response to ensure it's valid JSON
                # Remove markdown code block syntax if present
                if "```json" in analysis_result:
                    analysis_result = analysis_result.split("```json")[1].split("```")[0].strip()
                elif "```" in analysis_result:
                    analysis_result = analysis_result.split("```")[1].split("```")[0].strip()
                
                logger.debug(f"Cleaned analysis result: {analysis_result}")
                
                # Return the analysis result directly - frontend will handle JSON parsing
                return jsonify({"result": analysis_result})
                
            except Exception as e:
                logger.error(f"Error parsing JSON response: {str(e)}")
                # If JSON parsing fails, return the raw text
                return jsonify({
                    "result": response.text,
                    "note": "Couldn't parse as JSON, returning raw analysis"
                })
                
        except Exception as e:
            logger.error(f"Error from Gemini API: {str(e)}")
            return jsonify({"error": f"Error from Gemini API: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500














@app.route('/generate_workout', methods=['POST'])
def generate_workout():
    # Get user input and create voice coach option
    data = request.json
    voice_enabled = data.get('voice_enabled', False)  # New parameter for voice coaching
    if voice_enabled:
        # Add voice coaching instructions to the prompt
        base_prompt = """
        Act as an enthusiastic voice coach. Create a workout plan with verbal encouragement
        and clear vocal cues. Include motivational phrases between exercises.
        """
    else:
        base_prompt = ""

    # Get user input from the request
    mood = data.get('mood', 'Neutral')
    fitness_level = data.get('fitness_level', 'Intermediate')
    workout_type = data.get('workout_type', 'Full Body')
    duration = data.get('duration', '30')
    focus_areas = data.get('focus_areas', '')
    
    # Create prompt for Gemini
    prompt = f"""
    Create a workout plan with the following parameters:
    - User mood: {mood}
    - Fitness level: {fitness_level}
    - Workout type: {workout_type}
    - Desired workout duration: {duration} minutes
    - Focus areas: {focus_areas}
    
    Generate a workout plan that asks the user to perform specific exercises.
    Return a JSON array of exercises, each with:
    - 'name': The exercise name
    - 'duration': Duration in seconds
    - 'instructions': Brief instructions for proper form
    - 'intensity': A level from 1-5
    
    Format example:
    [
        {{
            "name": "Jumping Jacks",
            "duration": 30,
            "instructions": "Jump while spreading legs and arms",
            "intensity": 3
        }},
        {{
            "name": "Push-ups",
            "duration": 45,
            "instructions": "Keep your body straight, lower chest to ground",
            "intensity": 4
        }}
    ]
    
    Provide only the JSON array without any additional explanation.
    """
    
    # Generate response from Gemini
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    response = model.generate_content(prompt)
    
    # Process the response
    try:
        # Extract JSON content from the response
        content = response.text
        
        # Clean up the content if it contains markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        # Parse JSON to verify it's valid
        exercises = json.loads(content)
        return jsonify(exercises)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_mood_advice', methods=['POST'])
def get_mood_advice():
    mood = request.json.get('mood', 'Neutral')
    
    # Create prompt for Gemini
    prompt = f"""
    The user is feeling {mood} today before their workout. 
    
    1. Provide a short, motivational message (2-3 sentences) for their workout that acknowledges their mood.
    2. Suggest how they should approach their workout based on this mood.
    3. Recommend an appropriate exercise intensity.
    
    Format the response as JSON with the following structure:
    {{
        "message": "Your motivational message here",
        "approach": "Your workout approach suggestion",
        "intensity": "Your intensity recommendation"
    }}
    """
    
    # Generate response from Gemini
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    response = model.generate_content(prompt)
    
    try:
        # Extract JSON content from the response
        content = response.text
        
        # Clean up the content if it contains markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        # Parse JSON
        advice = json.loads(content)
        return jsonify(advice)
    except Exception as e:
        # Fallback if we can't parse JSON
        return jsonify({
            "message": f"Based on your {mood.lower()} mood, let's adapt your workout today.",
            "approach": "Listen to your body and adjust as needed.",
            "intensity": "Moderate"
        })

@app.route('/get_exercise_instructions', methods=['POST'])
def get_exercise_instructions():
    exercise = request.json.get('exercise', '')
    
    prompt = f"""
    Provide detailed but concise instructions for doing the exercise: {exercise}.
    Focus on proper form and technique. Include 3-4 key form tips.
    Limit your response to 3 short sentences.
    """
    
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    response = model.generate_content(prompt)
    
    return jsonify({"instructions": response.text})































@app.route('/api/analyze-fitness', methods=['POST'])
def analyze_fitness():
    try:
        # Get the form data from the request
        user_data = request.json
        
        # Prepare prompt for Gemini model
        prompt = f"""
        TASK: analyze_fitness
        
        Please analyze the following fitness assessment data and provide personalized recommendations.
        The response should include the following sections:
        - BMI calculation and category
        - Overall fitness score (0-100)
        - Health risk assessment for cardiovascular, musculoskeletal, metabolic, and stress categories
        - Personalized recommendations for exercise, nutrition, lifestyle, and any specialized needs
        - A summary of the assessment
        
        Format the response as a JSON object with the following structure:
        {{
            "bmi": float,
            "fitnessScore": int,
            "healthRisks": {{
                "cardiovascular": int,
                "musculoskeletal": int,
                "metabolic": int,
                "stress": int,
                "overall": int
            }},
            "recommendations": {{
                "exercise": [list of strings],
                "nutrition": [list of strings],
                "lifestyle": [list of strings],
                "specialized": [list of strings]
            }},
            "summary": string
        }}
        
        USER_DATA: {json.dumps(user_data)}
        """
        model_name = get_gemini_model_name()
        gemini_model = genai.get_model(model_name) 
        
        # Call Gemini model with the prompt
        response = gemini_model.generate_content(prompt)
        
        # Parse the response
        try:
            # First attempt to parse the response as JSON directly
            analysis_result = json.loads(response.text)
        except json.JSONDecodeError:
            # If direct parsing fails, extract JSON from the text response
            # This handles cases where the model might wrap the JSON in additional text
            response_text = response.text
            
            # Find JSON-like content and parse it
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = response_text[json_start:json_end]
                analysis_result = json.loads(json_content)
            else:
                # Fallback - create a basic response if JSON parsing fails
                analysis_result = {
                    "error": "Failed to parse model response",
                    "raw_response": response.text
                }
        
        return jsonify(analysis_result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "model": "gemini-2.0-flash",
        "timestamp": datetime.now().isoformat()
    })












# Store audio data in memory
audio_cache = {}

# Helper function to generate a more advanced synthetic waveform
def generate_synthetic_audio(mood, intensity, duration_sec, sound_types, 
                            tempo=120, reverb=0.3, frequency_shift=1.0, filter_cutoff=1000):
    sample_rate = 44100  # Hz
    amplitude = min(0.2 + (intensity / 5) * 0.3, 0.7)  # Scale intensity to appropriate amplitude
    duration_samples = int(duration_sec * sample_rate)
    
    # Base frequencies for different moods (in Hz)
    mood_frequencies = {
        'energetic': 440.0,  # A4
        'motivated': 392.0,  # G4
        'tired': 261.63,     # C4
        'stressed': 329.63,  # E4
        'happy': 349.23,     # F4
        'focus': 396.0,      # G4
        'meditation': 285.0,  # D4
        'relaxed': 330.0,    # E4
        'anxious': 466.16,   # A#4/Bb4
        'creative': 415.3,   # G#4/Ab4
        'melancholic': 311.13, # D#4/Eb4
    }
    
    base_freq = mood_frequencies.get(mood, 440.0) * frequency_shift
    
    # Initialize an empty audio array
    audio = np.zeros(duration_samples)
    
    # Tempo in beats per minute to seconds per beat
    seconds_per_beat = 60.0 / tempo
    samples_per_beat = int(seconds_per_beat * sample_rate)
    
    # Add components based on selected sound types
    if 'rhythm' in sound_types:
        # Add rhythmic beats with tempo consideration
        beat_interval = samples_per_beat  # Beat according to tempo
        for i in range(0, duration_samples, beat_interval):
            for j in range(min(4000, duration_samples - i)):
                decay = np.exp(-5 * j / 4000)
                audio[i + j] += amplitude * 0.6 * decay
    
    if 'melody' in sound_types:
        # Add a simple melody
        t = np.linspace(0, duration_sec, duration_samples, False)
        melody_freq = base_freq * 1.5  # Melody at a higher octave
        melody = amplitude * 0.4 * np.sin(2 * np.pi * melody_freq * t)
        # Add some variation
        for i in range(1, 4):
            melody += amplitude * 0.1 / i * np.sin(2 * np.pi * (melody_freq * i) * t)
        audio += melody
    
    if 'ambient' in sound_types:
        # Add ambient pad sound
        t = np.linspace(0, duration_sec, duration_samples, False)
        pad = amplitude * 0.3 * np.sin(2 * np.pi * base_freq * t)
        # Add harmonics
        pad += amplitude * 0.15 * np.sin(2 * np.pi * (base_freq * 1.5) * t)
        pad += amplitude * 0.1 * np.sin(2 * np.pi * (base_freq * 2) * t)
        audio += pad
    
    if 'effects' in sound_types:
        # Add occasional whoosh effects
        for i in range(0, duration_samples, sample_rate * 10):  # Every 10 seconds
            if i + sample_rate * 2 <= duration_samples:  # If there's enough room
                effect_duration = sample_rate * 2  # 2 seconds
                effect = np.zeros(effect_duration)
                t = np.linspace(0, 2, effect_duration, False)
                # Frequency sweep from low to high
                freq_sweep = base_freq/2 + t * base_freq
                effect = amplitude * 0.2 * np.sin(2 * np.pi * freq_sweep * t)
                # Apply envelope
                envelope = np.exp(-(t - 1) ** 2 * 2)
                effect *= envelope
                # Add to main audio
                audio[i:i+effect_duration] += effect
    
    if 'bass' in sound_types:
        # Add deep bass line
        t = np.linspace(0, duration_sec, duration_samples, False)
        bass_freq = base_freq / 2  # Bass at a lower octave
        bass = amplitude * 0.5 * np.sin(2 * np.pi * bass_freq * t)
        # Add some harmonic variation
        bass_pattern = np.sin(2 * np.pi * 0.5 * t)  # Slow modulation
        bass *= 0.7 + 0.3 * bass_pattern
        audio += bass
    
    if 'binaural' in sound_types:
        # Create binaural beat effect - we'll simulate it in mono
        # Real binaural would need stereo but this gives the frequency beating effect
        t = np.linspace(0, duration_sec, duration_samples, False)
        carrier_freq = base_freq  # Carrier frequency
        beat_freq = 5.0  # 5 Hz difference for theta waves (focus, meditation)
        if mood in ['energetic', 'motivated']:
            beat_freq = 15.0  # Higher for more energetic states
        
        binaural = amplitude * 0.4 * np.sin(2 * np.pi * carrier_freq * t)
        binaural += amplitude * 0.4 * np.sin(2 * np.pi * (carrier_freq + beat_freq) * t)
        audio += binaural
    
    # Apply low-pass filter (simple implementation)
    if filter_cutoff > 0:
        # Very simple low-pass filter approximation
        audio_fft = np.fft.rfft(audio)
        freq = np.fft.rfftfreq(len(audio), d=1/sample_rate)
        filter_mask = np.exp(-((freq / filter_cutoff) ** 2))
        audio_fft_filtered = audio_fft * filter_mask
        audio = np.fft.irfft(audio_fft_filtered, len(audio))
    
    # Apply simple reverb (very basic implementation)
    if reverb > 0:
        reverb_delay = int(sample_rate * 0.1)  # 100ms delay
        reverb_strength = reverb
        reverb_audio = np.zeros_like(audio)
        reverb_audio[reverb_delay:] = audio[:-reverb_delay] * reverb_strength
        audio = audio + reverb_audio
    
    # Normalize audio to prevent clipping
    if np.max(np.abs(audio)) > 1.0:
        audio = audio / np.max(np.abs(audio)) * 0.9
    
    return audio, sample_rate

# Function to generate music recommendations without external API
def generate_music_recommendation(mood, intensity):
    """Generate music recommendations without using external API"""
    
    # Define mood-based recommendations
    recommendations = {
        'energetic': {
            "music_style": "Upbeat Electronic",
            "frequency": "440",
            "tempo": "Fast-paced (140-160 BPM)",
            "description": "Energizing electronic music to boost your physical energy and mental alertness.",
            "instruments": ["Synthesizer", "Electronic Drums", "Bass", "Electric Guitar", "Digital Effects"],
            "playlist_suggestions": ["High Energy Workout Mix", "EDM Hits", "Power Running Playlist", "Cardio Boost", "Energy Rush"]
        },
        'motivated': {
            "music_style": "Inspirational Pop Rock",
            "frequency": "392",
            "tempo": "Medium-fast (120-140 BPM)",
            "description": "Uplifting music with motivational undertones to keep you inspired and focused on your goals.",
            "instruments": ["Piano", "Guitar", "Drums", "Orchestral Elements", "Vocals"],
            "playlist_suggestions": ["Motivational Anthems", "Success Soundtrack", "Achievement Mix", "Goal Crusher", "Victory Road"]
        },
        'tired': {
            "music_style": "Gentle Ambient",
            "frequency": "262",
            "tempo": "Slow (60-80 BPM)",
            "description": "Soothing ambient sounds to help you relax without draining your remaining energy.",
            "instruments": ["Ambient Synthesizer", "Piano", "Strings", "Light Percussion", "Nature Sounds"],
            "playlist_suggestions": ["Relaxation Station", "Gentle Recovery", "Calm Energy", "Peaceful Restoration", "Soft Revival"]
        },
        'stressed': {
            "music_style": "Calming Classical",
            "frequency": "330",
            "tempo": "Moderate (80-100 BPM)",
            "description": "Classical compositions known to reduce cortisol levels and promote mental relaxation.",
            "instruments": ["Piano", "Strings", "Woodwinds", "Harp", "Light Percussion"],
            "playlist_suggestions": ["Stress Relief Classics", "Calm Compositions", "Anxiety Reducing Melodies", "Mental Peace", "Tranquil Moments"]
        },
        'happy': {
            "music_style": "Cheerful Pop",
            "frequency": "349",
            "tempo": "Upbeat (120-130 BPM)",
            "description": "Bright, joyful music to enhance and maintain your positive mood.",
            "instruments": ["Piano", "Acoustic Guitar", "Upbeat Percussion", "Bass", "Cheerful Vocals"],
            "playlist_suggestions": ["Happy Hits", "Feel Good Playlist", "Sunshine Songs", "Joy Jams", "Positive Vibes Only"]
        },
        'focus': {
            "music_style": "Concentration Electronic",
            "frequency": "396",
            "tempo": "Steady (90-110 BPM)",
            "description": "Rhythmic, low-vocal electronic music designed to enhance concentration and flow state.",
            "instruments": ["Ambient Synthesizer", "Digital Piano", "Lo-Fi Beats", "Minimal Percussion", "Gentle Bass"],
            "playlist_suggestions": ["Deep Focus", "Concentration Enhancement", "Study Session", "Productive Flow", "Brain Boost"]
        },
        'meditation': {
            "music_style": "Meditative Ambient",
            "frequency": "285",
            "tempo": "Very slow (50-70 BPM)",
            "description": "Deep, resonant tones with minimal structure to facilitate meditation and mindfulness.",
            "instruments": ["Singing Bowls", "Ambient Pads", "Chimes", "Drone Instruments", "Nature Elements"],
            "playlist_suggestions": ["Meditation Journey", "Mindfulness Sounds", "Deep Relaxation", "Inner Peace", "Zen Garden"]
        },
        'relaxed': {
            "music_style": "Chillout Lounge",
            "frequency": "330",
            "tempo": "Relaxed (70-90 BPM)",
            "description": "Laid-back electronic and acoustic elements to maintain a pleasant, relaxed state.",
            "instruments": ["Mellow Synths", "Acoustic Guitar", "Soft Piano", "Light Percussion", "Ambient Pads"],
            "playlist_suggestions": ["Lounge Essentials", "Chill Afternoon", "Relaxed Vibes", "Easy Listening", "Smooth Acoustics"]
        },
        'anxious': {
            "music_style": "Calming New Age",
            "frequency": "466",
            "tempo": "Slow to moderate (60-90 BPM)",
            "description": "Gentle compositions designed to soothe anxiety and promote a sense of security.",
            "instruments": ["Soft Piano", "String Ensemble", "Wind Chimes", "Gentle Synths", "Nature Sounds"],
            "playlist_suggestions": ["Anxiety Relief", "Calm Nerves", "Peaceful Mind", "Stress Reduction", "Gentle Healing"]
        },
        'creative': {
            "music_style": "Eclectic Instrumental",
            "frequency": "415",
            "tempo": "Variable (90-120 BPM)",
            "description": "Diverse, interesting sounds and progressions to stimulate creative thinking and expression.",
            "instruments": ["Diverse Percussion", "Unique Synths", "World Instruments", "Atmospheric Pads", "Creative Samples"],
            "playlist_suggestions": ["Creative Flow", "Inspiration Mix", "Artist's Companion", "Idea Generator", "Creative Workshop"]
        },
        'melancholic': {
            "music_style": "Emotional Ambient",
            "frequency": "311",
            "tempo": "Slow (60-80 BPM)",
            "description": "Emotionally resonant music that acknowledges feelings of sadness while providing gentle comfort.",
            "instruments": ["Piano", "Cello", "Ambient Pads", "Subtle Strings", "Soft Vocals"],
            "playlist_suggestions": ["Melancholy Moments", "Emotional Healing", "Reflective Space", "Rainy Day Companion", "Gentle Catharsis"]
        }
    }
    
    # Intensity modifiers
    if intensity <= 2:
        # Lower intensity version
        recommendation = recommendations.get(mood, recommendations['focus'])
        recommendation["tempo"] = "Slower " + recommendation["tempo"].split("(")[0] + "(lower range)"
        recommendation["description"] = "Gentler version of " + recommendation["description"]
    elif intensity >= 4:
        # Higher intensity version
        recommendation = recommendations.get(mood, recommendations['energetic'])
        recommendation["tempo"] = "More intense " + recommendation["tempo"].split("(")[0] + "(upper range)"
        recommendation["description"] = "More powerful version of " + recommendation["description"]
    else:
        # Standard version
        recommendation = recommendations.get(mood, recommendations['focus'])
    
    return recommendation

@app.route('/api/generate_music', methods=['POST'])
def generate_music():
    try:
        data = request.json
        mood = data.get('mood', 'energetic')
        intensity = data.get('intensity', 3)
        duration_sec = data.get('duration', 300)  # Default to 5 minutes
        sound_types = data.get('soundTypes', ['rhythm', 'melody', 'ambient'])
        tempo = data.get('tempo', 120)
        reverb = data.get('reverb', 0.3)
        frequency_shift = data.get('freqShift', 1.0)
        filter_cutoff = data.get('filterCutoff', 1000)
        
        # Generate sound recommendation using Gemini
        prompt = f"""
        Create a detailed music recommendation for a {mood} mood with intensity level {intensity}/5.
        Format the response as a JSON object with these fields:
        - music_style: the general style or genre of music
        - frequency: a base frequency in Hz that's good for this mood
        - tempo: the tempo description
        - description: a brief description of how this music benefits the user
        - instruments: an array of 3-5 instruments that work well for this mood
        - playlist_suggestions: an array of 3-5 artist or song recommendations
        """
        
        try:
            model_name = get_gemini_model_name()
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # Extract JSON from response
            recommendation_text = response.text
            # Clean up the response text first
            cleaned_text = recommendation_text.replace('\n', ' ').strip()
            
            # Try parsing as direct JSON first
            try:
                recommendation_json = json.loads(cleaned_text)
            except json.JSONDecodeError:
                # Find JSON content using regex
                json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_text, re.DOTALL)
                if json_match:
                    recommendation_json = json.loads(json_match.group(1))
                else:
                    # Try to find the JSON without code blocks
                    json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                    if json_match:
                        recommendation_json = json.loads(json_match.group(0))
                    else:
                        # Fall back to our generated recommendation
                        recommendation_json = generate_music_recommendation(mood, intensity)
        except Exception as e:
            print(f"Error parsing recommendation: {str(e)}")
            recommendation_json = generate_music_recommendation(mood, intensity)
        
        # Generate audio file
        audio_data, sample_rate = generate_synthetic_audio(
            mood, intensity, duration_sec, sound_types, 
            tempo=tempo, reverb=reverb, 
            frequency_shift=frequency_shift, 
            filter_cutoff=filter_cutoff
        )
        
        # Create unique ID for this audio
        audio_id = f"{mood}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        
        # Store audio in memory cache
        audio_cache[audio_id] = (audio_data, sample_rate)
        
        # Return the audio ID instead of a file path
        return jsonify({
            "recommendation": recommendation_json,
            "audio_id": audio_id
        })
        
    except Exception as e:
        print(f"Error generating music: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/audio/<audio_id>')
def serve_audio(audio_id):
    """Serve the generated audio from memory cache"""
    if audio_id in audio_cache:
        audio_data, sample_rate = audio_cache[audio_id]
        
        # Create in-memory file object
        wav_file = io.BytesIO()
        sf.write(wav_file, audio_data, sample_rate, format='WAV')
        wav_file.seek(0)
        
        # Return audio file from memory
        return send_file(
            wav_file,
            mimetype='audio/wav',
            as_attachment=False,
            download_name=f"{audio_id}.wav"
        )
    else:
        return "Audio not found", 404

# Clean up old audio from memory periodically (implement if needed)
def cleanup_audio_cache():
    """Remove old audio from memory cache to prevent memory leaks"""
    current_time = datetime.now().timestamp()
    
    # Keep only audio generated in the last hour
    keys_to_delete = []
    for key in audio_cache:
        audio_time = int(key.split('_')[-1])
        if current_time - audio_time > 3600:  # More than an hour old
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del audio_cache[key]

# Routes for serving the application
@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')














def is_fitness_related(text):
    fitness_keywords = {
        'fitness', 'exercise', 'workout', 'gym', 'training',
        'muscle', 'strength', 'cardio', 'weight', 'nutrition',
        'diet', 'health', 'bodybuilding', 'running', 'yoga'
    }
    text = text.lower()
    return any(keyword in text for keyword in fitness_keywords)
@app.route('/get-fitness-news')
def get_fitness_news():
    articles = []
    # Use cached data if available and not expired
    cached_news = get_cached_news()
    
    if cached_news:
        return jsonify(cached_news)
        
    # Otherwise fetch from RSS feeds
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:  # Limit to 5 entries per feed
                if is_fitness_related(entry.title + " " + entry.get('summary', '')):
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'summary': entry.get('summary', 'No summary available.')[:200] + '...' if len(entry.get('summary', '')) > 200 else entry.get('summary', 'No summary available.')
                    })
        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")
    
    # Limit to 10 articles total
    articles = articles[:10]
    
    # Cache the results
    cache_news(articles)
    
    return jsonify(articles)

# News caching mechanism
NEWS_CACHE_FILE = 'news_cache.json'
NEWS_CACHE_EXPIRY = 24 * 60 * 60  # 24 hours in seconds

def get_cached_news():
    try:
        if os.path.exists(NEWS_CACHE_FILE):
            # Check if cache file exists and is not expired
            file_mod_time = os.path.getmtime(NEWS_CACHE_FILE)
            current_time = time.time()
            
            if current_time - file_mod_time < NEWS_CACHE_EXPIRY:
                with open(NEWS_CACHE_FILE, 'r') as f:
                    return json.load(f)
    except Exception as e:
        print(f"Error reading cache: {e}")
    
    return None

def cache_news(articles):
    try:
        with open(NEWS_CACHE_FILE, 'w') as f:
            json.dump(articles, f)
    except Exception as e:
        print(f"Error writing cache: {e}")

@app.route('/get-fitness-blogs')
def get_fitness_blogs():
    # This would typically be an API call to a blog service
    # For demo purposes, we'll return some mock data
    mock_blogs = [
        {
            "title": "The Ultimate Guide to HIIT Workouts",
            "author": "Jane Smith",
            "date": "May 2, 2025",
            "content": "High-Intensity Interval Training (HIIT) has revolutionized the fitness industry...",
            "views": "1,245",
            "comments": "32",
            "link": "https://example.com/hiit-workouts"
        },
        {
            "title": "Nutrition Myths Debunked: What Science Really Says",
            "author": "Dr. Michael Chen", 
            "date": "April 28, 2025",
            "content": "In this comprehensive analysis, we examine the most persistent nutrition myths...",
            "views": "2,876",
            "comments": "65",
            "link": "https://example.com/nutrition-myths"
        },
        {
            "title": "The Mind-Muscle Connection: Mental Techniques for Better Gains",
            "author": "Alex Rivera",
            "date": "April 25, 2025",
            "content": "While much attention is paid to workout routines and nutrition plans...",
            "views": "943",
            "comments": "27",
            "link": "https://example.com/mind-muscle-connection"
        }
    ]
    return jsonify(mock_blogs)

@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL is required"}), 400
    
    url = data['url']
    
    # In a real app, you would fetch the content from the URL first
    # For demo purposes, we'll assume we have the content
    
    try:
        # Using the official Google Generative AI library for Gemini
        model_name = get_gemini_model_name()
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""Summarize the following fitness blog article from URL: {url}. 
        Focus on the main points, key takeaways, and actionable advice.
        Keep the summary concise and informative."""
        
        response = model.generate_content(prompt)
        
        if response:
            summary = response.text
            if not summary:
                summary = "Unable to generate summary from API response."
        else:
            summary = "Error: No response from Gemini API"
            
    except Exception as e:
        summary = f"Error generating summary: {str(e)}"
    
    return jsonify({"summary": summary})










































# ------------------ RUN APP ------------------
if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    app.run(debug=True, port=5000)

