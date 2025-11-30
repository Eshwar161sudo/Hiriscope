let mediaStream = null;
let recognition = null;
let isRecording = false;
let recordingTimer = null;
let recordingSeconds = 0;
let emotionInterval = null;
let currentQuestion = '';
let currentEmotion = 'neutral';
let currentEmotionConfidence = 0;
let questionCount = 0;
let currentInterviewId = null;

const emotionEmojis = {
    confident: '😊',
    happy: '😄',
    neutral: '😐',
    nervous: '😰'
};

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ',
        warning: '⚠'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function openResumeModal() {
    const modal = document.getElementById('resumeModal');
    if (modal) {
        modal.classList.add('active');
        initResumeUpload();
    }
}

function closeResumeModal() {
    const modal = document.getElementById('resumeModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function initResumeUpload() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('resumeFile');
    const fileInfo = document.getElementById('fileInfo');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resumeForm = document.getElementById('resumeForm');
    const resultsDiv = document.getElementById('resumeResults');
    
    if (!uploadZone || !fileInput) return;
    
    uploadZone.onclick = () => fileInput.click();
    
    uploadZone.ondragover = (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    };
    
    uploadZone.ondragleave = () => {
        uploadZone.classList.remove('dragover');
    };
    
    uploadZone.ondrop = (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    };
    
    fileInput.onchange = () => {
        if (fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    };
    
    function handleFile(file) {
        const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!validTypes.includes(file.type) && !file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
            showToast('Please upload a PDF or DOCX file', 'error');
            return;
        }
        
        fileInfo.innerHTML = `📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        fileInfo.classList.remove('hidden');
        analyzeBtn.disabled = false;
        resultsDiv.classList.add('hidden');
    }
    
    resumeForm.onsubmit = async (e) => {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showToast('Please select a file first', 'error');
            return;
        }
        
        const btnText = analyzeBtn.querySelector('.btn-text');
        const btnLoader = analyzeBtn.querySelector('.btn-loader');
        
        btnText.textContent = 'Analyzing...';
        btnLoader.classList.remove('hidden');
        analyzeBtn.disabled = true;
        
        const formData = new FormData();
        formData.append('resume', file);
        
        try {
            const response = await fetch('/upload_resume', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                displayResumeResults(data);
                showToast('Resume analyzed successfully!', 'success');
            } else {
                showToast(data.error || 'Analysis failed', 'error');
            }
        } catch (error) {
            showToast('Error analyzing resume', 'error');
            console.error(error);
        } finally {
            btnText.textContent = 'Analyze Resume';
            btnLoader.classList.add('hidden');
            analyzeBtn.disabled = false;
        }
    };
}

function displayResumeResults(data) {
    const resultsDiv = document.getElementById('resumeResults');
    if (!resultsDiv) return;
    
    resultsDiv.innerHTML = `
        <div class="result-score">
            <div class="result-score-value">${data.score}%</div>
            <p style="color: var(--text-secondary); font-size: 13px;">Resume Score</p>
        </div>
        
        <div style="margin-bottom: 15px;">
            <p style="font-size: 12px; color: var(--primary-color); margin-bottom: 8px;">EXPERIENCE</p>
            <p style="font-size: 24px; font-weight: 600;">${data.experience_years} years</p>
        </div>
        
        <div style="margin-bottom: 15px;">
            <p style="font-size: 12px; color: var(--primary-color); margin-bottom: 8px;">DETECTED SKILLS</p>
            <div class="result-skills">
                ${data.skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('')}
            </div>
        </div>
        
        <div>
            <p style="font-size: 12px; color: var(--primary-color); margin-bottom: 8px;">SUGGESTIONS</p>
            <ul class="result-suggestions">
                ${data.suggestions.map(s => `<li>${s}</li>`).join('')}
            </ul>
        </div>
    `;
    
    resultsDiv.classList.remove('hidden');
}

function initInterview() {
    initCamera();
    initSpeechRecognition();
    setupEventListeners();
}

async function initCamera() {
    const video = document.getElementById('camera-feed');
    const overlay = document.getElementById('videoOverlay');
    const statusDot = document.querySelector('.video-status .status-dot');
    const statusText = document.querySelector('.video-status .status-text');
    
    if (!video) return;
    
    overlay.onclick = startCamera;
    
    async function startCamera() {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'user', width: 640, height: 480 },
                audio: false 
            });
            
            video.srcObject = mediaStream;
            overlay.classList.add('hidden');
            statusDot.classList.add('active');
            statusText.textContent = 'Camera Active';
            
            startEmotionAnalysis();
            
            showToast('Camera enabled successfully', 'success');
        } catch (error) {
            console.error('Camera error:', error);
            statusText.textContent = 'Camera Error';
            showToast('Could not access camera. Please check permissions.', 'error');
        }
    }
}

function startEmotionAnalysis() {
    if (emotionInterval) {
        clearInterval(emotionInterval);
    }
    
    emotionInterval = setInterval(captureAndAnalyzeEmotion, 2000);
}

async function captureAndAnalyzeEmotion() {
    const video = document.getElementById('camera-feed');
    const canvas = document.getElementById('captureCanvas');
    
    if (!video || !canvas || !mediaStream) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    
    ctx.drawImage(video, 0, 0);
    
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    
    try {
        const response = await fetch('/process_emotion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                image: imageData,
                interview_id: currentInterviewId
            })
        });
        
        const data = await response.json();
        updateEmotionDisplay(data);
    } catch (error) {
        console.error('Emotion analysis error:', error);
    }
}

function updateEmotionDisplay(data) {
    const emotions = ['confident', 'happy', 'neutral', 'nervous'];
    
    currentEmotion = data.emotion;
    currentEmotionConfidence = data.confidence;
    
    emotions.forEach(emotion => {
        const bar = document.getElementById(`${emotion}Bar`);
        const value = document.getElementById(`${emotion}Value`);
        
        if (bar && value) {
            const percent = emotion === data.emotion ? data.confidence : Math.random() * 30;
            bar.style.width = `${percent}%`;
            value.textContent = `${Math.round(percent)}%`;
        }
    });
    
    const currentEmotionDiv = document.getElementById('currentEmotion');
    if (currentEmotionDiv) {
        currentEmotionDiv.innerHTML = `
            <span class="emotion-icon">${emotionEmojis[data.emotion] || '😐'}</span>
            <span class="emotion-text">Current: ${data.emotion.charAt(0).toUpperCase() + data.emotion.slice(1)} (${data.confidence}% confidence)</span>
        `;
    }
}

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        showToast('Speech recognition not supported in this browser', 'warning');
        return;
    }
    
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    
    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        
        const transcriptBox = document.getElementById('transcriptBox');
        if (transcriptBox) {
            transcriptBox.textContent = transcript || 'Listening...';
        }
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (event.error !== 'no-speech') {
            showToast(`Speech error: ${event.error}`, 'error');
        }
    };
    
    recognition.onend = () => {
        if (isRecording) {
            recognition.start();
        }
    };
}

function setupEventListeners() {
    const newQuestionBtn = document.getElementById('newQuestionBtn');
    const recordBtn = document.getElementById('recordBtn');
    const submitBtn = document.getElementById('submitAnswerBtn');
    const finishBtn = document.getElementById('finishBtn');
    
    if (newQuestionBtn) {
        newQuestionBtn.onclick = fetchNewQuestion;
    }
    
    if (recordBtn) {
        recordBtn.onclick = toggleRecording;
    }
    
    if (submitBtn) {
        submitBtn.onclick = submitAnswer;
    }
    
    if (finishBtn) {
        finishBtn.onclick = finishSession;
    }
}

async function fetchNewQuestion() {
    try {
        const response = await fetch('/api/get_question');
        const data = await response.json();
        
        if (data.success) {
            questionCount++;
            currentQuestion = data.question;
            
            const questionText = document.getElementById('questionText');
            const questionNumber = document.getElementById('questionNumber');
            
            if (questionText) {
                questionText.textContent = data.question;
            }
            if (questionNumber) {
                questionNumber.textContent = `#${questionCount}`;
            }
            
            const transcriptBox = document.getElementById('transcriptBox');
            if (transcriptBox) {
                transcriptBox.textContent = 'Your speech will appear here in real-time...';
            }
            
            const feedbackCard = document.getElementById('feedbackCard');
            if (feedbackCard) {
                feedbackCard.classList.add('hidden');
            }
            
            const finishBtn = document.getElementById('finishBtn');
            if (finishBtn) {
                finishBtn.disabled = false;
            }
            
            showToast('New question loaded!', 'info');
        }
    } catch (error) {
        console.error('Error fetching question:', error);
        showToast('Error loading question', 'error');
    }
}

function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

function startRecording() {
    if (!currentQuestion) {
        showToast('Please get a question first', 'warning');
        return;
    }
    
    if (!recognition) {
        showToast('Speech recognition not available', 'error');
        return;
    }
    
    isRecording = true;
    recordingSeconds = 0;
    
    const recordBtn = document.getElementById('recordBtn');
    const statusIndicator = document.querySelector('.status-indicator');
    const statusMessage = document.querySelector('.status-message');
    const submitBtn = document.getElementById('submitAnswerBtn');
    
    if (recordBtn) {
        recordBtn.classList.add('recording');
        recordBtn.querySelector('.record-text').textContent = 'Stop Recording';
    }
    
    if (statusIndicator) {
        statusIndicator.classList.add('recording');
    }
    
    if (statusMessage) {
        statusMessage.textContent = 'Recording...';
    }
    
    if (submitBtn) {
        submitBtn.disabled = true;
    }
    
    recognition.start();
    
    recordingTimer = setInterval(() => {
        recordingSeconds++;
        updateTimer();
        
        if (recordingSeconds >= 30) {
            stopRecording();
            showToast('Maximum recording time reached (30s)', 'info');
        }
    }, 1000);
    
    showToast('Recording started - speak your answer', 'info');
}

function stopRecording() {
    isRecording = false;
    
    if (recognition) {
        recognition.stop();
    }
    
    if (recordingTimer) {
        clearInterval(recordingTimer);
    }
    
    const recordBtn = document.getElementById('recordBtn');
    const statusIndicator = document.querySelector('.status-indicator');
    const statusMessage = document.querySelector('.status-message');
    const submitBtn = document.getElementById('submitAnswerBtn');
    const transcriptBox = document.getElementById('transcriptBox');
    
    if (recordBtn) {
        recordBtn.classList.remove('recording');
        recordBtn.querySelector('.record-text').textContent = 'Start Recording';
    }
    
    if (statusIndicator) {
        statusIndicator.classList.remove('recording');
    }
    
    if (statusMessage) {
        statusMessage.textContent = 'Recording stopped';
    }
    
    if (submitBtn && transcriptBox && transcriptBox.textContent.length > 10) {
        submitBtn.disabled = false;
    }
    
    showToast('Recording stopped', 'info');
}

function updateTimer() {
    const timerDisplay = document.getElementById('recordingTimer');
    if (timerDisplay) {
        const minutes = Math.floor(recordingSeconds / 60);
        const seconds = recordingSeconds % 60;
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

async function submitAnswer() {
    const transcriptBox = document.getElementById('transcriptBox');
    const answer = transcriptBox ? transcriptBox.textContent : '';
    
    if (!answer || answer.length < 10 || answer === 'Your speech will appear here in real-time...') {
        showToast('Please record your answer first', 'warning');
        return;
    }
    
    const submitBtn = document.getElementById('submitAnswerBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    
    btnText.textContent = 'Analyzing...';
    btnLoader.classList.remove('hidden');
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/submit_answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: currentQuestion,
                answer: answer,
                emotion: currentEmotion,
                emotion_confidence: currentEmotionConfidence
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentInterviewId = data.interview_id;
            displayFeedback(data);
            showToast('Answer submitted successfully!', 'success');
        } else {
            showToast(data.error || 'Submission failed', 'error');
        }
    } catch (error) {
        console.error('Submit error:', error);
        showToast('Error submitting answer', 'error');
    } finally {
        btnText.textContent = 'Submit Answer';
        btnLoader.classList.add('hidden');
    }
}

function displayFeedback(data) {
    const feedbackCard = document.getElementById('feedbackCard');
    const scoreValue = document.getElementById('scoreValue');
    const scoreProgress = document.getElementById('scoreProgress');
    const feedbackText = document.getElementById('feedbackText');
    const semanticScore = document.getElementById('semanticScore');
    const voiceScore = document.getElementById('voiceScore');
    
    if (feedbackCard) {
        feedbackCard.classList.remove('hidden');
    }
    
    if (scoreValue) {
        scoreValue.textContent = data.score;
    }
    
    if (scoreProgress) {
        const circumference = 2 * Math.PI * 45;
        scoreProgress.style.strokeDasharray = circumference;
        scoreProgress.style.strokeDashoffset = circumference - (data.score / 100) * circumference;
    }
    
    if (feedbackText) {
        feedbackText.textContent = data.feedback;
    }
    
    if (semanticScore) {
        semanticScore.textContent = `${data.semantic_score}%`;
    }
    
    if (voiceScore) {
        voiceScore.textContent = `${data.voice_score}%`;
    }
}

function finishSession() {
    if (currentInterviewId) {
        window.location.href = `/results?id=${currentInterviewId}`;
    } else {
        window.location.href = '/results';
    }
}

window.onclick = (event) => {
    const modal = document.getElementById('resumeModal');
    if (event.target === modal) {
        closeResumeModal();
    }
};

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeResumeModal();
    }
});

window.addEventListener('beforeunload', () => {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
    }
    if (emotionInterval) {
        clearInterval(emotionInterval);
    }
    if (recognition) {
        recognition.stop();
    }
});

window.openResumeModal = openResumeModal;
window.closeResumeModal = closeResumeModal;
window.initInterview = initInterview;
