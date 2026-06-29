// --- Post Feed Render & Interaction Logic ---

let feedPage = 1;
let feedNextUrl = '/api/posts/feed/';
let loadingPosts = false;

document.addEventListener('DOMContentLoaded', () => {
    const feedContainer = document.getElementById('post-feed-list');
    if (feedContainer) {
        loadFeedPosts();
        initInfiniteScroll();
        loadSuggestions();
    }
});

function loadFeedPosts() {
    if (!feedNextUrl || loadingPosts) return;
    loadingPosts = true;

    const loader = document.getElementById('feed-loader');
    if (loader) loader.style.display = 'block';

    fetch(feedNextUrl)
        .then(res => res.json())
        .then(data => {
            feedNextUrl = data.next;
            renderPosts(data.results);
            loadingPosts = false;
            if (loader) loader.style.display = 'none';
        })
        .catch(err => {
            console.error('Error loading posts:', err);
            loadingPosts = false;
            if (loader) loader.style.display = 'none';
        });
}

function renderPosts(posts) {
    const feedContainer = document.getElementById('post-feed-list');
    if (!posts || posts.length === 0) {
        if (feedPage === 1) {
            feedContainer.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--text-secondary);" data-i18n="no_posts">
                    No posts yet. Start following users!
                </div>`;
        }
        return;
    }

    posts.forEach(post => {
        const postCard = document.createElement('div');
        postCard.className = 'post-card';
        postCard.id = `post-card-${post.id}`;

        // Media items mapping
        let mediaHtml = '';
        let controlsHtml = '';
        let dotsHtml = '';

        if (post.media && post.media.length > 0) {
            mediaHtml = `<div class="post-media-slider" id="slider-${post.id}">`;
            post.media.forEach((item, index) => {
                if (item.is_video) {
                    mediaHtml += `<video src="${item.file}" class="post-media-item" controls loop muted autoplay loading="lazy"></video>`;
                } else {
                    mediaHtml += `<img src="${item.file}" class="post-media-item" alt="Post media" loading="lazy">`;
                }
            });
            mediaHtml += `</div>`;

            if (post.media.length > 1) {
                controlsHtml = `
                    <button class="slider-btn prev" onclick="moveSlider(${post.id}, -1)">&#10094;</button>
                    <button class="slider-btn next" onclick="moveSlider(${post.id}, 1)">&#10095;</button>
                `;
                dotsHtml = `<div class="slider-dots" id="dots-${post.id}">`;
                post.media.forEach((_, idx) => {
                    dotsHtml += `<div class="dot ${idx === 0 ? 'active' : ''}"></div>`;
                });
                dotsHtml += `</div>`;
            }
        }

        // Post Structure
        postCard.innerHTML = `
            <div class="post-header">
                <div class="post-user-info">
                    <a href="/profile/${post.author_username}/">
                        <img src="${post.author_avatar || '/media/avatars/default.png'}" class="post-avatar" alt="${post.author_username}">
                    </a>
                    <div>
                        <a href="/profile/${post.author_username}/" class="post-username">
                            ${post.author_username}
                            ${post.author_is_verified ? `
                                <span class="verified-badge" title="Verified Creator" style="margin-left: 4px; display: inline-flex; align-items: center; color: var(--color-chakra-blue); vertical-align: middle;">
                                    <svg viewBox="0 0 24 24" fill="currentColor" style="width: 14px; height: 14px;"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                                </span>
                            ` : ''}
                        </a>
                        ${post.location ? `<div class="post-location">${post.location}</div>` : ''}
                    </div>
                </div>
            </div>
            
            <div class="post-media-container">
                ${mediaHtml}
                ${controlsHtml}
                ${dotsHtml}
            </div>

            <div class="post-actions">
                <div class="action-left">
                    <button class="action-btn ${post.is_liked ? 'liked' : ''}" id="like-btn-${post.id}" onclick="toggleLike(${post.id})">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
                        </svg>
                    </button>
                    <a href="/post/${post.id}/" class="action-btn">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/>
                        </svg>
                    </a>
                </div>
                <button class="action-btn ${post.is_saved ? 'saved' : ''}" id="save-btn-${post.id}" onclick="toggleSave(${post.id})">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/>
                    </svg>
                </button>
            </div>

            <div class="post-info-panel">
                <div class="likes-count"><span id="likes-count-${post.id}">${post.likes_count}</span> <span data-i18n="likes">likes</span></div>
                <div class="post-caption">
                    <a href="/profile/${post.author_username}/" class="username">
                        ${post.author_username}
                        ${post.author_is_verified ? `
                            <span class="verified-badge" title="Verified Creator" style="margin-left: 2px; display: inline-flex; align-items: center; color: var(--color-chakra-blue); vertical-align: middle;">
                                <svg viewBox="0 0 24 24" fill="currentColor" style="width: 12px; height: 12px;"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                            </span>
                        ` : ''}
                    </a>
                    <span>${formatCaption(post.caption)}</span>
                </div>
                ${post.comments_count > 0 ? `
                    <a href="/post/${post.id}/" class="comments-trigger">
                        View all ${post.comments_count} comments
                    </a>
                ` : ''}
                <div class="post-time">${formatDate(post.created_at)}</div>
            </div>

            <div class="comment-input-area">
                <input type="text" placeholder="Add a comment..." id="comment-input-${post.id}" onkeyup="handleCommentKeyUp(event, ${post.id})">
                <button class="comment-post-btn" onclick="submitComment(${post.id})" id="comment-btn-${post.id}" data-i18n="post_btn">Post</button>
            </div>
        `;

        feedContainer.appendChild(postCard);
    });
    
    // Apply client translations to new feed elements
    const savedLang = localStorage.getItem('lang') || 'en';
    if (typeof applyTranslations === 'function') {
        applyTranslations(savedLang);
    }
}

// --- Slider Control ---
const sliderIndexes = {};
function moveSlider(postId, direction) {
    const slider = document.getElementById(`slider-${postId}`);
    const dots = document.getElementById(`dots-${postId}`);
    if (!slider) return;

    if (!(postId in sliderIndexes)) {
        sliderIndexes[postId] = 0;
    }

    const mediaItemsCount = slider.children.length;
    let index = sliderIndexes[postId] + direction;

    if (index < 0) index = 0;
    if (index >= mediaItemsCount) index = mediaItemsCount - 1;

    sliderIndexes[postId] = index;
    slider.style.transform = `translateX(-${index * 100}%)`;

    // Update dots
    if (dots) {
        Array.from(dots.children).forEach((dot, idx) => {
            if (idx === index) {
                dot.classList.add('active');
            } else {
                dot.classList.remove('active');
            }
        });
    }
}

// --- Like Action ---
function toggleLike(postId) {
    const likeBtn = document.getElementById(`like-btn-${postId}`);
    const likesCountSpan = document.getElementById(`likes-count-${postId}`);
    const csrfToken = getCookie('csrftoken');

    fetch(`/api/posts/${postId}/like/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.liked) {
            likeBtn.classList.add('liked');
        } else {
            likeBtn.classList.remove('liked');
        }
        if (likesCountSpan) {
            likesCountSpan.textContent = data.likes_count;
        }
    })
    .catch(err => console.error('Error toggling like:', err));
}

// --- Save Action ---
function toggleSave(postId) {
    const saveBtn = document.getElementById(`save-btn-${postId}`);
    const csrfToken = getCookie('csrftoken');

    fetch(`/api/posts/${postId}/save/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.saved) {
            saveBtn.classList.add('saved');
        } else {
            saveBtn.classList.remove('saved');
        }
    })
    .catch(err => console.error('Error toggling save:', err));
}

// --- Add Comment ---
function handleCommentKeyUp(event, postId) {
    if (event.key === 'Enter') {
        submitComment(postId);
    }
}

function submitComment(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    const csrfToken = getCookie('csrftoken');
    const content = input.value.trim();

    if (!content) return;

    fetch(`/api/posts/${postId}/comments/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ content: content })
    })
    .then(res => {
        if (res.ok) {
            input.value = '';
            // Alert user or redirect to details to view comment thread
            window.location.href = `/post/${postId}/`;
        }
    })
    .catch(err => console.error('Error adding comment:', err));
}

// --- Suggestions Loader ---
function loadSuggestions() {
    const suggestionsList = document.getElementById('suggestions-list');
    if (!suggestionsList) return;

    fetch('/api/suggestions/')
        .then(res => res.json())
        .then(users => {
            suggestionsList.innerHTML = '';
            if (users.length === 0) {
                suggestionsList.innerHTML = '<div style="font-size:12px;color:var(--text-secondary);">No suggestions available</div>';
                return;
            }

            users.forEach(user => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.innerHTML = `
                    <div class="widget-user-details">
                        <a href="/profile/${user.username}/">
                            <img src="${user.profile.avatar || '/media/avatars/default.png'}" class="post-avatar" style="width:32px;height:32px;" alt="${user.username}">
                        </a>
                        <div>
                            <a href="/profile/${user.username}/" class="widget-username">
                                ${user.username}
                                ${user.is_verified ? `
                                    <span class="verified-badge" title="Verified Creator" style="margin-left: 2px; display: inline-flex; align-items: center; color: var(--color-chakra-blue); vertical-align: middle;">
                                        <svg viewBox="0 0 24 24" fill="currentColor" style="width: 12px; height: 12px;"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                                    </span>
                                ` : ''}
                            </a>
                            <div class="widget-name" style="font-size:11px;">Suggested for you</div>
                        </div>
                    </div>
                    <button class="follow-toggle-btn" onclick="followUser(${user.id}, this)">Follow</button>
                `;
                suggestionsList.appendChild(item);
            });
        })
        .catch(err => console.error('Error loading suggestions:', err));
}

function followUser(userId, buttonEl) {
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
            buttonEl.style.color = 'var(--text-secondary)';
        } else {
            buttonEl.textContent = 'Follow';
            buttonEl.style.color = '#0095f6';
        }
    })
    .catch(err => console.error('Error following user:', err));
}

// --- Helpers ---
function formatCaption(caption) {
    // Convert #hashtags to links
    return caption.replace(/#(\w+)/g, '<a href="/explore/?hashtag=$1">#$1</a>');
}

function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

// --- Infinite Scroll ---
function initInfiniteScroll() {
    const scrollTrigger = document.createElement('div');
    scrollTrigger.id = 'infinite-scroll-trigger';
    scrollTrigger.style.height = '10px';
    document.getElementById('post-feed-list').after(scrollTrigger);

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && feedNextUrl && !loadingPosts) {
                feedPage++;
                loadFeedPosts();
            }
        });
    }, { rootMargin: '200px' });

    observer.observe(scrollTrigger);
}
