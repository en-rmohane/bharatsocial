// --- Ephemeral Stories Carousel & Modal Logic ---

let activeStoryGroup = [];
let activeStoryIndex = 0;
let storyProgressTimer = null;
let currentProgressBar = null;
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
                <div class="story-modal-body">
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
    if (story.is_video) {
        viewport.innerHTML = `<video src="${story.media_file}" autoplay loop muted playsinline style="width:100%;height:100%;"></video>`;
    } else {
        viewport.innerHTML = `<img src="${story.media_file}" alt="Story media">`;
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
