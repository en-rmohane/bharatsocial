// --- Ephemeral Stories Carousel & Modal Logic ---

let activeStoryGroup = [];
let activeStoryIndex = 0;
let storyProgressTimer = null;
let currentProgressBar = null;
let storyAudioElement = null; // Background music player
const STORY_DURATION = 5000; // 5 seconds per story

function openStoriesModal(userStoriesJson) {
    activeStoryGroup = JSON.parse(decodeURIComponent(userStoriesJson));
    activeStoryIndex = 0;
    
    // Create and insert modal overlay
    let modal = document.getElementById('stories-view-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'stories-view-modal';
        modal.className = 'stories-modal-overlay';
        modal.innerHTML = `
            <div class="stories-modal-wrapper">
                <!-- Top Progress Bar Tray -->
                <div class="story-progress-tray" id="story-progress-tray"></div>
                
                <!-- Story Header -->
                <div class="story-modal-header">
                    <div class="story-modal-user">
                        <img src="" id="story-modal-avatar" class="post-avatar" style="width:32px;height:32px;">
                        <span id="story-modal-username" style="font-weight:600;font-size:14px;"></span>
                        <span id="story-modal-time" style="font-size:12px;color:rgba(255,255,255,0.7)"></span>
                    </div>
                    <button class="story-modal-close" onclick="closeStoriesModal()">&times;</button>
                </div>
                
                <!-- Main Content Media -->
                <div class="story-modal-body" style="position: relative;">
                    <!-- Music Badge Overlay -->
                    <div class="story-music-badge" id="story-music-badge">
                        <span>🎵</span> <span id="story-music-title"></span>
                    </div>
                    <button class="story-arrow left" onclick="prevStory()">&#10094;</button>
                    <div class="story-media-viewport" id="story-media-viewport"></div>
                    <button class="story-arrow right" onclick="nextStory()">&#10095;</button>
                </div>
                
                <!-- Bottom Emoji Reactions panel -->
                <div class="story-modal-footer">
                    <input type="text" placeholder="Send reply..." id="story-reply-input" onkeyup="handleStoryReplyKey(event)">
                    <div class="story-emojis">
                        <span onclick="sendStoryReaction('❤️')">❤️</span>
                        <span onclick="sendStoryReaction('🙌')">🙌</span>
                        <span onclick="sendStoryReaction('🔥')">🔥</span>
                        <span onclick="sendStoryReaction('👏')">👏</span>
                        <span onclick="sendStoryReaction('😂')">😂</span>
                        <span onclick="sendStoryReaction('😍')">😍</span>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Add matching inline styles for Stories Modal
        const style = document.createElement('style');
        style.textContent = `
            .stories-modal-overlay {
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background-color: rgba(0,0,0,0.95);
                z-index: 1000;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }
            .stories-modal-wrapper {
                width: 100%;
                max-width: 420px;
                height: 100vh;
                max-height: 800px;
                display: flex;
                flex-direction: column;
                position: relative;
                padding: 16px;
            }
            .story-progress-tray {
                display: flex;
                gap: 4px;
                width: 100%;
                margin-bottom: 12px;
            }
            .story-progress-bar-bg {
                flex-grow: 1;
                height: 3px;
                background-color: rgba(255,255,255,0.3);
                border-radius: 2px;
                overflow: hidden;
            }
            .story-progress-fill {
                height: 100%;
                width: 0%;
                background-color: white;
            }
            .story-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
            }
            .story-modal-user {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .story-modal-close {
                font-size: 28px;
                background: none;
                border: none;
                color: white;
                cursor: pointer;
            }
            .story-modal-body {
                flex-grow: 1;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: #000;
                border-radius: 8px;
                overflow: hidden;
            }
            .story-media-viewport {
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .story-media-viewport img, .story-media-viewport video {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            }
            .story-arrow {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(0,0,0,0.5);
                border: none;
                color: white;
                width: 36px;
                height: 36px;
                border-radius: 50%;
                cursor: pointer;
                z-index: 10;
            }
            .story-arrow.left { left: 12px; }
            .story-arrow.right { right: 12px; }
            .story-modal-footer {
                margin-top: 16px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .story-modal-footer input {
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 20px;
                padding: 10px 16px;
                font-size: 14px;
                color: white;
                background: none;
            }
            .story-modal-footer input::placeholder {
                color: rgba(255,255,255,0.5);
            }
            .story-emojis {
                display: flex;
                justify-content: space-around;
                font-size: 24px;
                cursor: pointer;
            }
            .story-emojis span {
                transition: transform 0.1s ease;
            }
            .story-emojis span:hover {
                transform: scale(1.2);
            }
            .story-music-badge {
                position: absolute;
                top: 16px;
                left: 16px;
                background-color: rgba(0,0,0,0.6);
                color: white;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: 600;
                display: none;
                align-items: center;
                gap: 6px;
                border: 1px solid rgba(255,255,255,0.2);
                z-index: 50;
            }
            /* Filters */
            .story-filter-vintage { filter: sepia(0.6) contrast(1.1) brightness(0.9); }
            .story-filter-bw { filter: grayscale(1) contrast(1.2); }
            .story-filter-warm { filter: saturate(1.4) sepia(0.2) hue-rotate(-10deg); }
            .story-filter-cool { filter: saturate(0.8) hue-rotate(180deg) brightness(1.05); }
            .story-filter-glow { filter: saturate(1.6) contrast(1.15) brightness(1.1); }
            /* Animations */
            .story-anim-zoom {
                animation: storyZoom 5s linear forwards;
            }
            @keyframes storyZoom {
                from { transform: scale(1); }
                to { transform: scale(1.12); }
            }
            .story-anim-pan {
                animation: storyPan 5s linear forwards;
            }
            @keyframes storyPan {
                from { transform: translate(-10px, 0) scale(1.05); }
                to { transform: translate(10px, 0) scale(1.05); }
            }
            .story-anim-fade {
                animation: storyFade 0.8s ease-out forwards;
            }
            @keyframes storyFade {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            .story-anim-spin {
                animation: storySpin 5s linear forwards;
            }
            @keyframes storySpin {
                from { transform: rotate(0deg) scale(1); }
                to { transform: rotate(2deg) scale(1.08); }
            }
        `;
        document.head.appendChild(style);
    }

    modal.style.display = 'flex';
    renderActiveStory();
}

function renderActiveStory() {
    if (activeStoryIndex >= activeStoryGroup.length) {
        closeStoriesModal();
        return;
    }

    const story = activeStoryGroup[activeStoryIndex];
    
    // Set user headers
    document.getElementById('story-modal-avatar').src = story.author_avatar || '/media/avatars/default.png';
    document.getElementById('story-modal-username').textContent = story.author_username;
    document.getElementById('story-modal-time').textContent = formatStoryTime(story.created_at);

    // Setup viewport media
    const viewport = document.getElementById('story-media-viewport');
    let mediaHtml = '';
    
    // Compile CSS classes for filters and animations
    let classes = [];
    if (story.filter_style && story.filter_style !== 'none') {
        classes.push(`story-filter-${story.filter_style}`);
    }
    if (story.animation_style && story.animation_style !== 'none') {
        classes.push(`story-anim-${story.animation_style}`);
    }
    const classStr = classes.join(' ');

    if (story.is_video) {
        mediaHtml = `<video src="${story.media_file}" class="${classStr}" autoplay loop muted playsinline style="width:100%;height:100%;"></video>`;
    } else {
        mediaHtml = `<img src="${story.media_file}" class="${classStr}" alt="Story media">`;
    }
    viewport.innerHTML = mediaHtml;

    // Handle background music playback
    if (storyAudioElement) {
        storyAudioElement.pause();
        storyAudioElement = null;
    }

    const musicBadge = document.getElementById('story-music-badge');
    const musicTitle = document.getElementById('story-music-title');
    if (story.music_url && story.music_url !== '') {
        musicTitle.textContent = story.music_title || 'Background Music';
        musicBadge.style.display = 'flex';
        
        storyAudioElement = new Audio(story.music_url);
        storyAudioElement.loop = true;
        // catch to handle auto-play restrictions gracefully
        storyAudioElement.play().catch(e => console.debug("Audio autoplay prevented, user interaction required: ", e));
    } else {
        musicBadge.style.display = 'none';
    }

    // Build Progress Indicators
    const tray = document.getElementById('story-progress-tray');
    tray.innerHTML = '';
    activeStoryGroup.forEach((_, idx) => {
        const bg = document.createElement('div');
        bg.className = 'story-progress-bar-bg';
        const fill = document.createElement('div');
        fill.className = 'story-progress-fill';
        
        if (idx < activeStoryIndex) {
            fill.style.width = '100%';
        }
        bg.appendChild(fill);
        tray.appendChild(bg);
    });

    // Mark story as viewed
    markStoryViewed(story.id);

    // Start progress timer animation
    startStoryTimer();
}

function startStoryTimer() {
    if (storyProgressTimer) clearInterval(storyProgressTimer);
    
    const fills = document.querySelectorAll('.story-progress-fill');
    currentProgressBar = fills[activeStoryIndex];
    let width = 0;
    const interval = 50; // Update every 50ms
    const step = 100 / (STORY_DURATION / interval);

    storyProgressTimer = setInterval(() => {
        width += step;
        if (width >= 100) {
            width = 100;
            clearInterval(storyProgressTimer);
            nextStory();
        }
        if (currentProgressBar) currentProgressBar.style.width = `${width}%`;
    }, interval);
}

function nextStory() {
    activeStoryIndex++;
    if (activeStoryIndex >= activeStoryGroup.length) {
        closeStoriesModal();
    } else {
        renderActiveStory();
    }
}

function prevStory() {
    activeStoryIndex--;
    if (activeStoryIndex < 0) {
        activeStoryIndex = 0;
    }
    renderActiveStory();
}

function closeStoriesModal() {
    if (storyProgressTimer) clearInterval(storyProgressTimer);
    if (storyAudioElement) {
        storyAudioElement.pause();
        storyAudioElement = null;
    }
    const modal = document.getElementById('stories-view-modal');
    if (modal) modal.style.display = 'none';
}

function markStoryViewed(storyId) {
    const csrfToken = getCookie('csrftoken');
    fetch(`/api/stories/${storyId}/view/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .catch(err => console.debug('Logging views failed...'));
}

function handleStoryReplyKey(e) {
    if (e.key === 'Enter') {
        const input = document.getElementById('story-reply-input');
        if (input.value.trim()) {
            sendStoryReaction(`Reply: ${input.value.trim()}`);
            input.value = '';
        }
    }
}

function sendStoryReaction(emoji) {
    if (activeStoryIndex >= activeStoryGroup.length) return;
    const story = activeStoryGroup[activeStoryIndex];
    const csrfToken = getCookie('csrftoken');

    fetch(`/api/stories/${story.id}/react/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ reaction_type: emoji })
    })
    .then(res => res.json())
    .then(data => {
        // Show success animation or toast
        showReactionToast(emoji);
    })
    .catch(err => console.error('Error sending story reaction:', err));
}

function showReactionToast(emoji) {
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.top = '50%';
    toast.style.left = '50%';
    toast.style.transform = 'translate(-50%, -50%) scale(0)';
    toast.style.fontSize = '80px';
    toast.style.zIndex = '2000';
    toast.style.transition = 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
    toast.innerText = emoji;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.transform = 'translate(-50%, -50%) scale(1)';
    }, 50);

    setTimeout(() => {
        toast.style.transform = 'translate(-50%, -50%) scale(0)';
        setTimeout(() => toast.remove(), 400);
    }, 1200);
}

function formatStoryTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffHours = Math.floor((now - date) / 3600000);
    if (diffHours < 1) {
        const diffMins = Math.floor((now - date) / 60000);
        return `${diffMins}m ago`;
    }
    return `${diffHours}h ago`;
}

// --- Visual Story Editor / Creator Modal Logic ---
let selectedMusicUrl = '';
let selectedMusicTitle = '';
let selectedFilter = 'none';
let selectedAnimation = 'none';
let previewAudioElement = null;

function openStoryEditor(file) {
    selectedMusicUrl = '';
    selectedMusicTitle = '';
    selectedFilter = 'none';
    selectedAnimation = 'none';
    if (previewAudioElement) {
        previewAudioElement.pause();
        previewAudioElement = null;
    }

    let editorModal = document.getElementById('story-creator-modal');
    if (!editorModal) {
        editorModal = document.createElement('div');
        editorModal.id = 'story-creator-modal';
        editorModal.className = 'story-creator-overlay';
        document.body.appendChild(editorModal);
        
        const style = document.createElement('style');
        style.textContent = `
            .story-creator-overlay {
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background-color: rgba(0,0,0,0.9);
                z-index: 1100;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }
            .story-creator-wrapper {
                width: 100%;
                max-width: 440px;
                background-color: var(--bg-primary);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-md);
                display: flex;
                flex-direction: column;
                padding: 20px;
                max-height: 95vh;
                overflow-y: auto;
                color: var(--text-primary);
                box-shadow: var(--shadow-large);
            }
            .creator-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 12px;
            }
            .creator-preview-container {
                width: 100%;
                height: 300px;
                background-color: #000;
                border-radius: var(--radius-sm);
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                margin-bottom: 20px;
            }
            .creator-preview-container img, .creator-preview-container video {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                transition: filter 0.2s ease;
            }
            .creator-options {
                display: flex;
                flex-direction: column;
                gap: 16px;
                margin-bottom: 20px;
            }
            .creator-section {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .creator-section label {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary);
                text-align: left;
            }
            .creator-select {
                width: 100%;
                padding: 10px;
                border: 1px solid var(--border-color);
                border-radius: var(--radius-sm);
                background-color: var(--bg-secondary);
                color: var(--text-primary);
                font-size: 14px;
            }
            .creator-buttons {
                display: flex;
                gap: 12px;
            }
            .creator-btn {
                flex: 1;
                padding: 12px;
                border-radius: var(--radius-sm);
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                border: 1px solid var(--border-color);
                text-align: center;
            }
            .creator-btn.cancel {
                background-color: var(--bg-secondary);
                color: var(--text-primary);
            }
            .creator-btn.share {
                background: var(--accent-gradient);
                color: white;
                border: none;
            }
        `;
        document.head.appendChild(style);
    }

    const isVideo = file.type.startsWith('video/');
    const fileUrl = URL.createObjectURL(file);
    
    editorModal.innerHTML = `
        <div class="story-creator-wrapper">
            <div class="creator-header">
                <span style="font-weight:700;font-size:16px;">Story Editor</span>
                <span style="cursor:pointer;font-size:20px;" onclick="closeStoryEditor()">&times;</span>
            </div>
            
            <div class="creator-preview-container" id="creator-preview-box">
                ${isVideo ? 
                    `<video src="${fileUrl}" autoplay loop muted playsinline style="width:100%;height:100%;"></video>` :
                    `<img src="${fileUrl}" alt="Story preview" id="creator-preview-img">`
                }
            </div>
            
            <div class="creator-options">
                <div class="creator-section">
                    <label>🎵 Select Music Track</label>
                    <select class="creator-select" onchange="handleCreatorMusicChange(this.value)">
                        <option value="">No Music</option>
                        <option value="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3|Tum Tum - Upbeat Mix">Tum Tum - Upbeat Mix</option>
                        <option value="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3|Vibe of India - Flute">Vibe of India - Flute Melody</option>
                        <option value="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3|Lofi Sunset Vibes">Lofi Sunset Vibes</option>
                        <option value="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3|Traditional Modern Sitar">Traditional Modern Sitar</option>
                    </select>
                </div>
                
                <div class="creator-section">
                    <label>✨ Select Filter Effect</label>
                    <select class="creator-select" onchange="handleCreatorFilterChange(this.value)">
                        <option value="none">Normal / None</option>
                        <option value="vintage">Vintage (Sepia)</option>
                        <option value="bw">Black & White (Grayscale)</option>
                        <option value="warm">Warm Sunshine</option>
                        <option value="cool">Cool Breeze</option>
                        <option value="glow">Vibrant Glow</option>
                    </select>
                </div>
                
                <div class="creator-section">
                    <label>🎬 Select Entrance Animation</label>
                    <select class="creator-select" onchange="handleCreatorAnimationChange(this.value)">
                        <option value="none">None / Standard</option>
                        <option value="zoom">Smooth Zoom In</option>
                        <option value="pan">Cinematic Pan</option>
                        <option value="fade">Gentle Fade In</option>
                        <option value="spin">Slow Spin Zoom</option>
                    </select>
                </div>
            </div>
            
            <div class="creator-buttons">
                <button class="creator-btn cancel" onclick="closeStoryEditor()">Cancel</button>
                <button class="creator-btn share" id="post-story-submit-btn">Share Story</button>
            </div>
        </div>
    `;

    document.getElementById('post-story-submit-btn').onclick = function() {
        submitStoryWithEffects(file);
    };

    editorModal.style.display = 'flex';
}

function closeStoryEditor() {
    const editorModal = document.getElementById('story-creator-modal');
    if (editorModal) editorModal.style.display = 'none';
    if (previewAudioElement) {
        previewAudioElement.pause();
        previewAudioElement = null;
    }
}

function handleCreatorMusicChange(val) {
    if (previewAudioElement) {
        previewAudioElement.pause();
        previewAudioElement = null;
    }
    
    if (val === '') {
        selectedMusicUrl = '';
        selectedMusicTitle = '';
        return;
    }
    
    const parts = val.split('|');
    selectedMusicUrl = parts[0];
    selectedMusicTitle = parts[1];
    
    previewAudioElement = new Audio(selectedMusicUrl);
    previewAudioElement.loop = true;
    previewAudioElement.play().catch(e => console.debug("Preview play prevented"));
}

function handleCreatorFilterChange(val) {
    selectedFilter = val;
    const mediaEl = document.querySelector('#creator-preview-box img, #creator-preview-box video');
    if (!mediaEl) return;
    
    mediaEl.className = '';
    
    if (val !== 'none') {
        mediaEl.classList.add(`story-filter-${val}`);
    }
}

function handleCreatorAnimationChange(val) {
    selectedAnimation = val;
    const mediaEl = document.querySelector('#creator-preview-box img, #creator-preview-box video');
    if (!mediaEl) return;
    
    mediaEl.className = '';
    if (selectedFilter !== 'none') {
        mediaEl.classList.add(`story-filter-${selectedFilter}`);
    }
    
    if (val !== 'none') {
        mediaEl.classList.add(`story-anim-${val}`);
        
        mediaEl.style.animation = 'none';
        mediaEl.offsetHeight; 
        mediaEl.style.animation = null;
    }
}

function submitStoryWithEffects(file) {
    const btn = document.getElementById('post-story-submit-btn');
    btn.disabled = true;
    btn.textContent = 'Sharing...';
    
    const csrfToken = getCookie('csrftoken');
    const formData = new FormData();
    formData.append('media_file', file);
    formData.append('music_url', selectedMusicUrl);
    formData.append('music_title', selectedMusicTitle);
    formData.append('filter_style', selectedFilter);
    formData.append('animation_style', selectedAnimation);

    fetch('/api/stories/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(res => {
        if (res.ok) {
            alert('Story shared successfully!');
            window.location.reload();
        } else {
            alert('Upload failed.');
            btn.disabled = false;
            btn.textContent = 'Share Story';
        }
    })
    .catch(err => {
        console.error('Story upload error:', err);
        btn.disabled = false;
        btn.textContent = 'Share Story';
    });
}
