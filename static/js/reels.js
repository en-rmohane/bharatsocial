// --- Reels Video Feed Autoplay & Interactions ---

document.addEventListener('DOMContentLoaded', () => {
    const reelsContainer = document.getElementById('reels-container');
    if (reelsContainer) {
        loadReels();
        initAutoplayObserver();
    }
});

function loadReels() {
    const container = document.getElementById('reels-container');
    
    fetch('/api/reels/')
        .then(res => res.json())
        .then(reels => {
            container.innerHTML = '';
            if (reels.length === 0) {
                container.innerHTML = `<div style="color: white; text-align: center; padding: 40px;">No reels uploaded yet.</div>`;
                return;
            }

            reels.forEach(reel => {
                const card = document.createElement('div');
                card.className = 'reel-card';
                card.id = `reel-card-${reel.id}`;
                card.innerHTML = `
                    <div class="reel-video-container">
                        <video class="reel-video" src="${reel.video_file}" loop muted playsinline onclick="toggleVideoPlayback(this)"></video>
                        <div class="reel-sound-overlay" onclick="toggleMuteAll(event)">
                            <svg viewBox="0 0 24 24" id="sound-icon" fill="white" width="24" height="24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
                        </div>
                    </div>
                    
                    <!-- Right floating options overlay -->
                    <div class="reel-actions">
                        <button class="reel-action-btn ${reel.is_liked ? 'liked' : ''}" onclick="toggleLikeReel(${reel.id}, this)">
                            <div class="action-icon-circle">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>
                            </div>
                            <span class="count">${reel.likes_count}</span>
                        </button>

                        <button class="reel-action-btn" onclick="openReelComments(${reel.id})">
                            <div class="action-icon-circle">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/></svg>
                            </div>
                            <span class="count">${reel.comments_count}</span>
                        </button>
                    </div>

                    <!-- Bottom caption overlay -->
                    <div class="reel-meta-bottom">
                        <div class="reel-user-row">
                            <img src="${reel.author_avatar || '/media/avatars/default.png'}" class="reel-avatar" alt="${reel.author_username}">
                            <span class="reel-username">${reel.author_username}</span>
                            <span class="dot-separator">•</span>
                            <button class="reel-follow-btn" onclick="followReelUser(${reel.author}, this)">Follow</button>
                        </div>
                        <p class="reel-caption">${reel.caption}</p>
                    </div>
                `;
                container.appendChild(card);
            });
            
            // Trigger playback on first reel load
            setTimeout(() => {
                const firstVideo = document.querySelector('.reel-video');
                if (firstVideo) firstVideo.play().catch(e => console.log("User interaction required to start video"));
            }, 500);
        })
        .catch(err => console.error('Error loading reels:', err));
}

// --- Video Autoplay Observer ---
function initAutoplayObserver() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const video = entry.target.querySelector('video');
            if (!video) return;

            if (entry.isIntersecting) {
                video.play().catch(e => console.log('Autoplay blocked'));
            } else {
                video.pause();
            }
        });
    }, {
        threshold: 0.6 // Reel is active if 60% in view
    });

    // Dynamic child observation
    const container = document.getElementById('reels-container');
    if (container) {
        const observerConfig = { childList: true };
        const observerCallback = (mutationsList) => {
            for (const mutation of mutationsList) {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(node => {
                        if (node.classList && node.classList.contains('reel-card')) {
                            observer.observe(node);
                        }
                    });
                }
            }
        };
        const configObserver = new MutationObserver(observerCallback);
        configObserver.observe(container, observerConfig);
    }
}

function toggleVideoPlayback(video) {
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
}

let allVideosMuted = true;
function toggleMuteAll(event) {
    event.stopPropagation();
    allVideosMuted = !allVideosMuted;
    
    document.querySelectorAll('.reel-video').forEach(video => {
        video.muted = allVideosMuted;
    });

    // Toggle Icons
    document.querySelectorAll('.reel-sound-overlay svg').forEach(svg => {
        if (allVideosMuted) {
            svg.innerHTML = `<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.21.05-.42.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73 4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>`;
        } else {
            svg.innerHTML = `<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>`;
        }
    });
}

// --- Reel Liking ---
function toggleLikeReel(reelId, buttonEl) {
    const csrfToken = getCookie('csrftoken');
    const countSpan = buttonEl.querySelector('.count');

    fetch(`/api/reels/${reelId}/like/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.liked) {
            buttonEl.classList.add('liked');
        } else {
            buttonEl.classList.remove('liked');
        }
        countSpan.textContent = data.likes_count;
    })
    .catch(err => console.error('Error toggling like:', err));
}

// --- Follow User ---
function followReelUser(userId, buttonEl) {
    const csrfToken = getCookie('csrftoken');
    fetch(`/api/follow/${userId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.is_following) {
            buttonEl.textContent = 'Following';
        } else {
            buttonEl.textContent = 'Follow';
        }
    })
    .catch(err => console.error('Error following reel author:', err));
}

// --- Comments Sliding Drawer ---
let activeReelId = null;

function openReelComments(reelId) {
    activeReelId = reelId;
    const drawer = document.getElementById('reels-comments-drawer');
    const list = document.getElementById('reels-comments-list');
    
    if (!drawer || !list) return;

    drawer.classList.add('active');
    list.innerHTML = `<div style="color:var(--text-secondary);text-align:center;padding:20px;">Loading comments...</div>`;

    fetch(`/api/reels/${reelId}/comments/`)
        .then(res => res.json())
        .then(comments => {
            list.innerHTML = '';
            if (comments.length === 0) {
                list.innerHTML = `<div style="color:var(--text-secondary);text-align:center;padding:20px;">No comments yet</div>`;
                return;
            }

            comments.forEach(comment => {
                const el = document.createElement('div');
                el.className = 'drawer-comment-item';
                el.innerHTML = `
                    <img src="${comment.author_avatar || '/media/avatars/default.png'}" class="post-avatar" style="width:30px;height:30px;" alt="${comment.author_username}">
                    <div style="flex-grow:1;">
                        <span style="font-weight:600;font-size:13px;margin-right:8px;">${comment.author_username}</span>
                        <span style="font-size:13px;">${comment.content}</span>
                    </div>
                `;
                list.appendChild(el);
            });
        })
        .catch(err => console.error('Error fetching comments:', err));
}

function closeReelComments() {
    const drawer = document.getElementById('reels-comments-drawer');
    if (drawer) drawer.classList.remove('active');
    activeReelId = null;
}

function postReelComment() {
    const input = document.getElementById('reels-comment-input');
    if (!input || !activeReelId) return;

    const content = input.value.trim();
    if (!content) return;

    const csrfToken = getCookie('csrftoken');

    fetch(`/api/reels/${activeReelId}/comments/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ content: content })
    })
    .then(res => res.json())
    .then(comment => {
        input.value = '';
        openReelComments(activeReelId); // Reload comments
    })
    .catch(err => console.error('Error posting reel comment:', err));
}
