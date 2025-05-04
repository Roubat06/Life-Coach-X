document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const musicForm = document.getElementById('music-form');
    const generateButton = document.getElementById('generate-button');
    const recommendationDisplay = document.getElementById('recommendation-display');
    const errorNotification = document.getElementById('error-notification');
    const advancedToggle = document.getElementById('advanced-toggle');
    const advancedOptions = document.getElementById('advanced-options');
    
    // Sliders
    const intensitySlider = document.getElementById('intensity');
    const intensityValue = document.getElementById('intensity-value');
    const tempoSlider = document.getElementById('tempo');
    const tempoValue = document.getElementById('tempo-value');
    const reverbSlider = document.getElementById('reverb');
    const reverbValue = document.getElementById('reverb-value');
    const freqShiftSlider = document.getElementById('freqShift');
    const freqShiftValue = document.getElementById('freqShift-value');
    const filterCutoffSlider = document.getElementById('filterCutoff');
    const filterCutoffValue = document.getElementById('filterCutoff-value');
    
    // Audio player state
    let audioContext;
    let audioPlayer;
    let currentAudioId = null;
    
    // Initialize UI
    initializeUI();
    
    // Form submission
    musicForm.addEventListener('submit', function(e) {
        e.preventDefault();
        generateMusic();
    });
    
    // Initialize UI elements
    function initializeUI() {
        // Set up slider value displays
        setupSlider(intensitySlider, intensityValue);
        setupSlider(tempoSlider, tempoValue);
        setupSlider(reverbSlider, reverbValue, 1);
        setupSlider(freqShiftSlider, freqShiftValue, 1);
        setupSlider(filterCutoffSlider, filterCutoffValue);
        
        // Advanced options toggle
        advancedToggle.addEventListener('click', function() {
            advancedOptions.style.display = advancedOptions.style.display === 'block' ? 'none' : 'block';
            const icon = advancedToggle.querySelector('i');
            icon.className = advancedOptions.style.display === 'block' ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
        });
    }
    
    // Set up slider and its value display
    function setupSlider(slider, valueDisplay, decimals = 0) {
        valueDisplay.textContent = parseFloat(slider.value).toFixed(decimals);
        
        slider.addEventListener('input', function() {
            valueDisplay.textContent = parseFloat(this.value).toFixed(decimals);
        });
    }
    
    // Format time for audio player (seconds to MM:SS)
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }
    
    // Generate music from form data
    async function generateMusic() {
        // Show loading state
        generateButton.classList.add('btn-loading');
        generateButton.disabled = true;
        errorNotification.style.display = 'none';
        
        // Get form data
        const mood = document.getElementById('mood').value;
        const intensity = parseInt(intensitySlider.value);
        const soundTypes = Array.from(document.querySelectorAll('input[name="soundTypes"]:checked')).map(el => el.value);
        const duration = parseInt(document.getElementById('duration').value);
        const tempo = parseInt(tempoSlider.value);
        const reverb = parseFloat(reverbSlider.value);
        const freqShift = parseFloat(freqShiftSlider.value);
        const filterCutoff = parseInt(filterCutoffSlider.value);
        
        // Prepare request data
        const requestData = {
            mood,
            intensity,
            soundTypes,
            duration,
            tempo,
            reverb,
            freqShift,
            filterCutoff
        };
        
        try {
            // Send request to the API
            const response = await fetch('/api/generate_music', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            // Check for errors
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Server response:', data); // Add logging to debug
            
            if (!data.recommendation || !data.audio_id) {
                throw new Error('Invalid server response format');
            }
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Display recommendation and audio player
            displayMusicRecommendation(data.recommendation, data.audio_id);
            
        } catch (error) {
            console.error('Error generating music:', error);
            errorNotification.innerHTML = `<p>Error: ${error.message || 'Unable to generate music. Please try again.'}</p>`;
            errorNotification.style.display = 'block';
            
            // Scroll to error
            errorNotification.scrollIntoView({ behavior: 'smooth' });
        } finally {
            // Reset button state
            generateButton.classList.remove('btn-loading');
            generateButton.disabled = false;
        }
    }
    
    // Display music recommendation and audio player
    function displayMusicRecommendation(recommendation, audioId) {
        // Save current audio ID
        currentAudioId = audioId;
        
        // Create tags HTML
        const instrumentsHTML = recommendation.instruments.map(instrument => 
            `<span class="tag">${instrument}</span>`
        ).join('');
        
        const playlistHTML = recommendation.playlist_suggestions.map(suggestion => 
            `<span class="tag">${suggestion}</span>`
        ).join('');
        
        // Build recommendation HTML
        const recommendationHTML = `
            <div class="result-card">
                <h2 class="result-heading">Your Personalized Music Therapy</h2>
                
                <div class="info-section">
                    <div class="info-item">
                        <span class="info-label">Music Style</span>
                        <div class="info-value">${recommendation.music_style}</div>
                    </div>
                    
                    <div class="info-item">
                        <span class="info-label">Tempo</span>
                        <div class="info-value">${recommendation.tempo}</div>
                    </div>
                    
                    <div class="info-item">
                        <span class="info-label">Base Frequency</span>
                        <div class="info-value">${recommendation.frequency} Hz</div>
                    </div>
                    
                    <div class="info-item">
                        <span class="info-label">Recommended Instruments</span>
                        <div class="tag-list">
                            ${instrumentsHTML}
                        </div>
                    </div>
                </div>
                
                <div class="description">
                    <p>${recommendation.description}</p>
                </div>
                
                <div class="info-item">
                    <span class="info-label">Playlist Suggestions</span>
                    <div class="tag-list">
                        ${playlistHTML}
                    </div>
                </div>
                
                <div class="audio-player">
                    <h3>Listen to Your Therapeutic Sound</h3>
                    <div class="audio-controls">
                        <div class="play-button" id="play-button">
                            <i class="fas fa-play" id="play-icon"></i>
                        </div>
                        
                        <div class="progress-container">
                            <div class="progress-bar" id="progress-bar">
                                <div class="progress" id="progress"></div>
                            </div>
                            <div class="time">
                                <span id="current-time">0:00</span>
                                <span id="duration-time">0:00</span>
                            </div>
                        </div>
                        
                        <div class="volume-container">
                            <div class="volume-icon">
                                <i class="fas fa-volume-up" id="volume-icon"></i>
                            </div>
                            <input type="range" class="volume-slider" id="volume-slider" min="0" max="1" step="0.1" value="0.7">
                        </div>
                    </div>
                    
                    <button class="download-button" id="download-button">
                        <i class="fas fa-download"></i> Download Audio
                    </button>
                </div>
            </div>
        `;
        
        // Update the display
        recommendationDisplay.innerHTML = recommendationHTML;
        
        // Scroll to the recommendation
        recommendationDisplay.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Set up audio player
        setupAudioPlayer(audioId);
        
        // Set up download button
        document.getElementById('download-button').addEventListener('click', function() {
            window.location.href = `/api/audio/${audioId}?download=true`;
        });
    }
    
    // Set up the audio player functionality
    function setupAudioPlayer(audioId) {
        // Audio elements
        const playButton = document.getElementById('play-button');
        const playIcon = document.getElementById('play-icon');
        const progressBar = document.getElementById('progress-bar');
        const progress = document.getElementById('progress');
        const currentTimeDisplay = document.getElementById('current-time');
        const durationTimeDisplay = document.getElementById('duration-time');
        const volumeSlider = document.getElementById('volume-slider');
        const volumeIcon = document.getElementById('volume-icon');
        
        // Create audio element
        const audio = new Audio(`/api/audio/${audioId}`);
        audioPlayer = audio;
        
        // Set initial volume
        audio.volume = volumeSlider.value;
        
        // When audio metadata is loaded
        audio.addEventListener('loadedmetadata', function() {
            durationTimeDisplay.textContent = formatTime(audio.duration);
        });
        
        // Play/pause button
        playButton.addEventListener('click', function() {
            if (audio.paused) {
                audio.play();
                playIcon.className = 'fas fa-pause';
            } else {
                audio.pause();
                playIcon.className = 'fas fa-play';
            }
        });
        
        // Update progress bar during playback
        audio.addEventListener('timeupdate', function() {
            const progressPercent = (audio.currentTime / audio.duration) * 100;
            progress.style.width = progressPercent + '%';
            currentTimeDisplay.textContent = formatTime(audio.currentTime);
        });
        
        // Click on progress bar to seek
        progressBar.addEventListener('click', function(e) {
            const seekPosition = (e.offsetX / this.offsetWidth);
            audio.currentTime = seekPosition * audio.duration;
        });
        
        // Volume control
        volumeSlider.addEventListener('input', function() {
            audio.volume = this.value;
            updateVolumeIcon(this.value);
        });
        
        // Update volume icon based on level
        function updateVolumeIcon(volume) {
            if (volume >= 0.6) {
                volumeIcon.className = 'fas fa-volume-up';
            } else if (volume > 0) {
                volumeIcon.className = 'fas fa-volume-down';
            } else {
                volumeIcon.className = 'fas fa-volume-mute';
            }
        }
        
        // Toggle mute on volume icon click
        volumeIcon.addEventListener('click', function() {
            if (audio.volume > 0) {
                audio.volume = 0;
                volumeSlider.value = 0;
                volumeIcon.className = 'fas fa-volume-mute';
            } else {
                audio.volume = 0.7;
                volumeSlider.value = 0.7;
                volumeIcon.className = 'fas fa-volume-up';
            }
        });
        
        // When audio ends
        audio.addEventListener('ended', function() {
            playIcon.className = 'fas fa-play';
            progress.style.width = '0%';
            audio.currentTime = 0;
        });
        
        // Handle errors
        audio.addEventListener('error', function() {
            errorNotification.innerHTML = '<p>Error playing audio. Please try generating a new track.</p>';
            errorNotification.style.display = 'block';
        });
    }
    
    // Clean up when leaving the page
    window.addEventListener('beforeunload', function() {
        if (audioPlayer) {
            audioPlayer.pause();
            audioPlayer = null;
        }
    });
});