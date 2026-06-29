// --- Long-Polling Direct Messaging Logic with E2EE ---

let activeUsername = null;
let pollIntervalId = null;
let chatMessagesList = [];

// --- E2EE Encryption Helpers ---
function getSharedKey(userA, userB) {
    const sorted = [userA, userB].sort();
    return `${sorted[0]}_${sorted[1]}`;
}

const E2EE_PREFIX = "🔒[E2EE]:";

function encryptMessage(plaintext, key) {
    let ciphertext = "";
    for (let i = 0; i < plaintext.length; i++) {
        const charCode = plaintext.charCodeAt(i);
        const keyChar = key.charCodeAt(i % key.length);
        ciphertext += String.fromCharCode(charCode ^ keyChar);
    }
    const base64Cipher = btoa(unescape(encodeURIComponent(ciphertext)));
    return E2EE_PREFIX + base64Cipher;
}

function decryptMessage(ciphertext, key) {
    if (!ciphertext || !ciphertext.startsWith(E2EE_PREFIX)) {
        return ciphertext; // Return plain text if not E2EE
    }
    try {
        const base64Part = ciphertext.substring(E2EE_PREFIX.length);
        const decoded = decodeURIComponent(escape(atob(base64Part)));
        let plaintext = "";
        for (let i = 0; i < decoded.length; i++) {
            const charCode = decoded.charCodeAt(i);
            const keyChar = key.charCodeAt(i % key.length);
            plaintext += String.fromCharCode(charCode ^ keyChar);
        }
        return plaintext;
    } catch (e) {
        console.error("Decryption error:", e);
        return "[Decryption failed]";
    }
}

function initChat() {
    const inboxList = document.getElementById('chat-inbox-users');
    if (inboxList) {
        loadChatUsers();
        setInterval(loadChatUsers, 10000); // Refresh user list counts every 10 seconds
        
        // Listen for image selection
        const imageInput = document.getElementById('chat-image-input');
        if (imageInput) {
            imageInput.addEventListener('change', () => {
                if (imageInput.files.length > 0) {
                    sendAttachment();
                }
            });
        }

        // Listen for chat user search input
        const searchInput = document.getElementById('chat-user-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.trim();
                if (query.length > 0) {
                    searchUsersForChat(query);
                } else {
                    loadChatUsers();
                }
            });
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}

function loadChatUsers() {
    const list = document.getElementById('chat-inbox-users');
    if (!list) return;

    fetch('/api/chat/users/')
        .then(res => {
            if (!res.ok) {
                throw new Error(`Server returned status ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            try {
                // Check if we need to preserve selection
                const activeId = activeUsername;
                list.innerHTML = '';

                const recentChats = data.recent_chats || [];
                const suggestedUsers = data.suggested_users || [];

                // 1. Render Recent Chats Section
                const recentHeader = document.createElement('div');
                recentHeader.className = 'chat-section-header';
                recentHeader.textContent = 'Recent Chats / बातचीत';
                list.appendChild(recentHeader);

                if (recentChats.length === 0) {
                    const emptyRecent = document.createElement('div');
                    emptyRecent.style.cssText = 'text-align:center;padding:24px;color:var(--text-secondary);font-size:12px;font-style:italic;';
                    emptyRecent.textContent = 'No recent conversations / कोई बातचीत नहीं';
                    list.appendChild(emptyRecent);
                } else {
                    recentChats.forEach(user => {
                        list.appendChild(createUserItemDOM(user, activeId));
                    });
                }

                // 2. Render Suggested Friends Section
                if (suggestedUsers.length > 0) {
                    const suggestedHeader = document.createElement('div');
                    suggestedHeader.className = 'chat-section-header';
                    suggestedHeader.textContent = 'Suggested Friends / सुझाए गए मित्र';
                    list.appendChild(suggestedHeader);

                    suggestedUsers.forEach(user => {
                        list.appendChild(createUserItemDOM(user, activeId));
                    });
                }

                // Auto-select the first user in recent chats if no active thread is set
                if (!activeUsername && recentChats.length > 0) {
                    const pathParts = window.location.pathname.split('/').filter(Boolean);
                    const pathUsername = (pathParts.length >= 3 && pathParts[0] === 'direct' && pathParts[1] === 't') ? pathParts[2] : null;
                    
                    if (!pathUsername) {
                        selectThread(recentChats[0].username);
                    }
                }
            } catch (err) {
                list.innerHTML = `<div style="text-align:center;padding:20px;color:red;font-size:11px;">Rendering Error: ${err.message}</div>`;
                console.error("Chat Rendering Error:", err);
            }
        })
        .catch(err => {
            list.innerHTML = `<div style="text-align:center;padding:20px;color:red;font-size:11px;">Fetch Error: ${err.message}</div>`;
            console.error('Error loading chat users:', err);
        });
}

function createUserItemDOM(user, activeId) {
    const item = document.createElement('div');
    item.className = `chat-user-item ${user.username === activeId ? 'active' : ''}`;
    item.onclick = () => selectThread(user.username);
    
    // Decrypt last message preview if E2EE
    let displayMsg = user.last_message || "";
    if (displayMsg.startsWith(E2EE_PREFIX) && typeof currentLoggedInUsername !== 'undefined') {
        const key = getSharedKey(currentLoggedInUsername, user.username);
        displayMsg = decryptMessage(displayMsg, key);
    }

    const nameToDisplay = (user.first_name || user.last_name) 
        ? `${user.first_name} ${user.last_name}`.trim() 
        : user.username;

    item.innerHTML = `
        <div class="avatar-wrapper">
            <img src="${user.avatar}" class="chat-item-avatar" alt="${user.username}">
            ${user.is_online ? `<div class="online-dot"></div>` : ''}
        </div>
        <div class="chat-item-details">
            <div class="chat-item-name-row">
                <span class="chat-item-username" style="display:none;">${user.username}</span>
                <span class="chat-item-displayname" style="font-size:14px; font-weight:600;">${nameToDisplay}</span>
                <span class="chat-item-time">${formatTime(user.last_message_time)}</span>
            </div>
            <div class="chat-item-message-row">
                <span class="chat-item-preview">${displayMsg}</span>
                ${user.unread_count > 0 ? `<span class="chat-item-unread-badge">${user.unread_count}</span>` : ''}
            </div>
        </div>
    `;
    return item;
}

function selectThread(username) {
    activeUsername = username;
    
    // UI elements update
    document.querySelectorAll('.chat-user-item').forEach(item => {
        const itemUser = item.querySelector('.chat-item-username').textContent;
        if (itemUser === username) {
            item.classList.add('active');
            const unreadBadge = item.querySelector('.chat-item-unread-badge');
            if (unreadBadge) unreadBadge.remove();
        } else {
            item.classList.remove('active');
        }
    });

    // Show Chat Box, Hide Empty State
    document.getElementById('chat-box-empty').style.display = 'none';
    const threadPanel = document.getElementById('chat-thread-active');
    threadPanel.style.display = 'flex';

    // Populate active user header details
    document.getElementById('chat-active-username').textContent = username;
    
    // Fetch details of active user avatar
    fetch('/api/chat/users/')
        .then(res => res.json())
        .then(data => {
            const allUsers = [...(data.recent_chats || []), ...(data.suggested_users || [])];
            const current = allUsers.find(u => u.username === username);
            if (current) {
                document.getElementById('chat-active-avatar').src = current.avatar;
                document.getElementById('chat-active-status').textContent = current.is_online ? 'Online' : 'Offline';
            }
        });

    loadMessages();
    
    // Reset Polling for real-time message stream
    if (pollIntervalId) clearInterval(pollIntervalId);
    pollIntervalId = setInterval(loadMessages, 3000); // Fetch thread updates every 3 seconds

    // Update browser URL without reloading
    if (window.history.replaceState) {
        window.history.replaceState(null, "", `/direct/t/${username}/`);
    }

    // Toggle CSS classes for mobile layout responsiveness
    const leftPane = document.getElementById('chat-left-users-pane');
    const rightPane = document.querySelector('.chat-right-pane');
    if (leftPane && rightPane) {
        leftPane.classList.add('hidden-mobile');
        rightPane.classList.add('show-mobile');
    }

    // Clear search box on selecting a user to reset the view
    const searchInput = document.getElementById('chat-user-search-input');
    if (searchInput && searchInput.value) {
        searchInput.value = '';
        loadChatUsers();
    }
}

function goBackToUserList() {
    activeUsername = null;
    if (pollIntervalId) {
        clearInterval(pollIntervalId);
        pollIntervalId = null;
    }
    
    const leftPane = document.getElementById('chat-left-users-pane');
    const rightPane = document.querySelector('.chat-right-pane');
    if (leftPane && rightPane) {
        leftPane.classList.remove('hidden-mobile');
        rightPane.classList.remove('show-mobile');
    }
    
    if (window.history.replaceState) {
        window.history.replaceState(null, "", "/direct/t/");
    }
}

function searchUsersForChat(query) {
    const list = document.getElementById('chat-inbox-users');
    if (!list) return;

    fetch(`/posts/api/search/autocomplete/?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
            list.innerHTML = '';

            const searchHeader = document.createElement('div');
            searchHeader.className = 'chat-section-header';
            searchHeader.textContent = 'Search Results / खोज परिणाम';
            list.appendChild(searchHeader);

            const users = data.users || [];
            if (users.length === 0) {
                const emptySearch = document.createElement('div');
                emptySearch.style.cssText = 'text-align:center;padding:24px;color:var(--text-secondary);font-size:12px;font-style:italic;';
                emptySearch.textContent = 'No users found / कोई उपयोगकर्ता नहीं मिला';
                list.appendChild(emptySearch);
            } else {
                users.forEach(user => {
                    const chatUser = {
                        id: null,
                        username: user.username,
                        first_name: '',
                        last_name: '',
                        avatar: user.avatar,
                        is_online: false,
                        last_message: '',
                        last_message_time: null,
                        unread_count: 0
                    };
                    list.appendChild(createUserItemDOM(chatUser, activeUsername));
                });
            }
        })
        .catch(err => console.error('Error searching chat users:', err));
}

function loadMessages() {
    if (!activeUsername) return;

    fetch(`/api/chat/messages/${activeUsername}/`)
        .then(res => res.json())
        .then(messages => {
            const container = document.getElementById('chat-messages-scroll');
            
            // Check if messages count or payload is different to prevent layout refresh jitter
            if (messages.length === chatMessagesList.length) return;
            
            chatMessagesList = messages;
            container.innerHTML = '';
            
            messages.forEach(msg => {
                const bubbleWrapper = document.createElement('div');
                const isOutgoing = msg.sender_username !== activeUsername;
                bubbleWrapper.className = `message-bubble-wrapper ${isOutgoing ? 'outgoing' : 'incoming'}`;
                
                let mediaHtml = '';
                let displayMsg = msg.content || "";
                
                if (msg.is_snap) {
                    if (msg.is_expired) {
                        mediaHtml = `<div class="snap-message-placeholder expired">👻 Snap (Expired)</div>`;
                        displayMsg = "";
                    } else {
                        const isOutgoing = msg.sender_username !== activeUsername;
                        if (isOutgoing) {
                            mediaHtml = `<div class="snap-message-placeholder expired">👻 Snap (Sent)</div>`;
                        } else {
                            mediaHtml = `
                                <div class="snap-message-placeholder" onclick="playSnapMessage(${msg.id}, '${msg.image}', '${encodeURIComponent(msg.content)}')">
                                    <span>👻 View Snap (5s)</span>
                                </div>
                            `;
                        }
                        displayMsg = "";
                    }
                } else if (msg.image) {
                    const lowerUrl = msg.image.toLowerCase();
                    if (lowerUrl.endsWith('.mp4') || lowerUrl.endsWith('.mov') || lowerUrl.endsWith('.webm') || lowerUrl.endsWith('.avi')) {
                        mediaHtml = `<video src="${msg.image}" class="message-image" style="max-width: 240px; max-height: 240px; border-radius: var(--radius-md);" controls></video>`;
                    } else {
                        mediaHtml = `<img src="${msg.image}" class="message-image" alt="Shared image" onclick="window.open('${msg.image}')">`;
                    }
                }

                // Decrypt message content if E2EE
                if (displayMsg && displayMsg.startsWith(E2EE_PREFIX) && typeof currentLoggedInUsername !== 'undefined') {
                    const key = getSharedKey(currentLoggedInUsername, activeUsername);
                    displayMsg = decryptMessage(displayMsg, key);
                }

                // Append delete button inside message row
                bubbleWrapper.innerHTML = `
                    ${mediaHtml}
                    <div style="display: flex; align-items: center; gap: 8px; width: 100%; justify-content: ${isOutgoing ? 'flex-end' : 'flex-start'}; position: relative;" class="message-row-inner">
                        ${isOutgoing ? `<button class="delete-msg-btn" onclick="deleteMessage(${msg.id})" title="Delete message" style="font-size: 11px; opacity: 0.4; cursor: pointer; background: none; border: none; padding: 4px; display: inline-flex; align-items: center; justify-content: center; margin-right: 4px; color: var(--text-muted); transition: var(--transition);">🗑️</button>` : ''}
                        ${displayMsg ? `<div class="message-bubble">${displayMsg}</div>` : ''}
                        ${!isOutgoing ? `<button class="delete-msg-btn" onclick="deleteMessage(${msg.id})" title="Delete message" style="font-size: 11px; opacity: 0.4; cursor: pointer; background: none; border: none; padding: 4px; display: inline-flex; align-items: center; justify-content: center; margin-left: 4px; color: var(--text-muted); transition: var(--transition);">🗑️</button>` : ''}
                    </div>
                    <span class="message-timestamp">${formatMsgTime(msg.created_at)}</span>
                `;
                container.appendChild(bubbleWrapper);
            });
            
            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
        })
        .catch(err => console.error('Error fetching messages:', err));
}

function handleChatKeyUp(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function sendMessage() {
    const input = document.getElementById('chat-text-input');
    if (!input || !activeUsername) return;

    const content = input.value.trim();
    if (!content) return;

    // Encrypt the message before sending to the server
    let encryptedContent = content;
    let key = "";
    if (typeof currentLoggedInUsername !== 'undefined') {
        key = getSharedKey(currentLoggedInUsername, activeUsername);
        encryptedContent = encryptMessage(content, key);
    }

    const csrfToken = getCookie('csrftoken');
    input.value = '';

    fetch(`/api/chat/messages/${activeUsername}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ content: encryptedContent })
    })
    .then(res => res.json())
    .then(msg => {
        chatMessagesList.push(msg);
        
        let displayContent = msg.content;
        if (displayContent.startsWith(E2EE_PREFIX) && key) {
            displayContent = decryptMessage(displayContent, key);
        }

        // Append bubble directly for instant UX feedback
        const container = document.getElementById('chat-messages-scroll');
        const bubbleWrapper = document.createElement('div');
        bubbleWrapper.className = 'message-bubble-wrapper outgoing';
        bubbleWrapper.innerHTML = `
            <div class="message-bubble">${displayContent}</div>
            <span class="message-timestamp">${formatMsgTime(msg.created_at)}</span>
        `;
        container.appendChild(bubbleWrapper);
        container.scrollTop = container.scrollHeight;
        
        // Reload user list ordering
        loadChatUsers();
    })
    .catch(err => console.error('Error sending message:', err));
}

function triggerImageUpload() {
    document.getElementById('chat-image-input').click();
}

function sendAttachment() {
    const imageInput = document.getElementById('chat-image-input');
    if (!imageInput || imageInput.files.length === 0 || !activeUsername) return;

    const file = imageInput.files[0];
    const csrfToken = getCookie('csrftoken');
    const formData = new FormData();
    formData.append('image', file);

    imageInput.value = ''; // Reset trigger

    fetch(`/api/chat/messages/${activeUsername}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(res => res.json())
    .then(msg => {
        chatMessagesList.push(msg);
        loadMessages();
        loadChatUsers();
    })
    .catch(err => console.error('Error sending image attachment:', err));
}

// --- Time Helpers ---
function formatTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function formatMsgTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) + ' • ' + date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

// --- Message & Thread Deletion Handlers ---
function deleteMessage(messageId) {
    if (!confirm("Are you sure you want to delete this message? (क्या आप इस संदेश को हटाना चाहते हैं?)")) {
        return;
    }
    const csrfToken = getCookie('csrftoken');
    fetch(`/api/chat/messages/delete/${messageId}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            chatMessagesList = chatMessagesList.filter(msg => msg.id !== messageId);
            loadMessages();
            loadChatUsers();
        } else {
            alert("Failed to delete message: " + (data.error || "Unknown error"));
        }
    })
    .catch(err => console.error('Error deleting message:', err));
}

function deleteActiveThread() {
    if (!activeUsername) return;
    if (!confirm(`Are you sure you want to delete the entire chat with ${activeUsername}? (क्या आप ${activeUsername} के साथ पूरी चैट हटाना चाहते हैं?)`)) {
        return;
    }
    const csrfToken = getCookie('csrftoken');
    fetch(`/api/chat/messages/delete-thread/${activeUsername}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            chatMessagesList = [];
            const container = document.getElementById('chat-messages-scroll');
            if (container) container.innerHTML = '';
            
            // Go back to inbox empty state
            document.getElementById('chat-thread-active').style.display = 'none';
            document.getElementById('chat-box-empty').style.display = 'flex';
            activeUsername = null;
            
            // Clear URL
            if (window.history.replaceState) {
                window.history.replaceState(null, "", "/direct/t/");
            }
            
            // Reset mobile state if needed
            const leftPane = document.getElementById('chat-left-users-pane');
            const rightPane = document.querySelector('.chat-right-pane');
            if (leftPane && rightPane) {
                leftPane.classList.remove('hidden-mobile');
                rightPane.classList.remove('show-mobile');
            }
            
            loadChatUsers();
        } else {
            alert("Failed to delete thread: " + (data.error || "Unknown error"));
        }
    })
    .catch(err => console.error('Error deleting thread:', err));
}

// --- Snapchat Lenses Camera & Disappearing Snaps Engine ---
let localCameraStream = null;
let mediaRecorderInstance = null;
let recordedChunks = [];
let selectedSnapFilter = 'none';
let recordedSnapBlob = null;
let recordingCountdownInterval = null;
const SNAP_RECORDING_DURATION = 5000; // 5 seconds maximum

// AR props variables
let selectedARProp = 'none';
let selectedARPropEmoji = '';
let propXOffset = 0;
let propYOffset = -40; // centered slightly up (for glasses/nose/crown relative to center)
let propScale = 1.0;
let canvasAnimationId = null;

const AR_PROPS = [
    { id: 'none', name: '❌ Clear Mask', emoji: '' },
    // --- Glasses & Eyewear (15 items) ---
    { id: 'goggles', name: '🕶️ Cool Shades', emoji: '🕶️' },
    { id: 'glasses', name: '👓 Nerd Glasses', emoji: '👓' },
    { id: 'starglasses', name: '🌟 Star Glasses', emoji: '🌟' },
    { id: 'heartglasses', name: '❤️ Heart Eyes', emoji: '❤️' },
    { id: 'pinkshades', name: '🕶️🌸 Pink Shades', emoji: '🕶️' },
    { id: 'anime-eyes', name: '👀 Anime Eyes', emoji: '👀' },
    { id: 'monocle', name: '🧐 Monocle Glass', emoji: '🧐' },
    { id: 'thuglife', name: '🕶️ Thug Life', emoji: '🕶️' },
    { id: 'fire-eyes', name: '🔥 Fire Eyes', emoji: '🔥' },
    { id: 'money-eyes', name: '🤑 Dollar Eyes', emoji: '🤑' },
    { id: 'rainbow-glasses', name: '🌈 Rainbow Visor', emoji: '🥽' },
    { id: 'cyber-visor', name: '🤖 Cyber Goggles', emoji: '🥽' },
    { id: 'alien-visor', name: '👽 Alien Visor', emoji: '🥽' },
    { id: '3d-glasses', name: '🕶️ 3D Glasses', emoji: '🕶️' },
    { id: 'pirate-patch', name: '🏴‍☠️ Pirate Patch', emoji: '👁️‍🗨️' },

    // --- Hats & Crowns (15 items) ---
    { id: 'crown', name: '👑 Royal Crown', emoji: '👑' },
    { id: 'hat', name: '🎩 Retro Hat', emoji: '🎩' },
    { id: 'tiara', name: '👑✨ Princess Tiara', emoji: '👑' },
    { id: 'heart-crown', name: '👑💕 Heart Crown', emoji: '👑' },
    { id: 'flower-crown', name: '🌸👑 Flower Tiara', emoji: '👑' },
    { id: 'chef-hat', name: '👨‍🍳 Chef Hat', emoji: '👨‍🍳' },
    { id: 'cowboy-hat', name: '🤠 Cowboy Hat', emoji: '🤠' },
    { id: 'santa-hat', name: '🎅 Santa Hat', emoji: '🎅' },
    { id: 'graduation-cap', name: '🎓 Graduate Cap', emoji: '🎓' },
    { id: 'witch-hat', name: '🧙 Witch Hat', emoji: '🧙' },
    { id: 'military-helmet', name: '🪖 Commando Cap', emoji: '🪖' },
    { id: 'police-cap', name: '👮 Police Cap', emoji: '👮' },
    { id: 'birthday-cap', name: '🥳 Party Cap', emoji: '🥳' },
    { id: 'halo', name: '😇 Angel Halo', emoji: '😇' },
    { id: 'turband', name: '👳 Desi Turban', emoji: '👳' },

    // --- Animals & Face Features (10 items) ---
    { id: 'catears', name: '🐱 Cat Ears', emoji: '🐱' },
    { id: 'dogears', name: '🐶 Dog Ears', emoji: '🐶' },
    { id: 'bunny-ears', name: '🐰 Bunny Ears', emoji: '🐰' },
    { id: 'horns', name: '😈 Neon Horns', emoji: '😈' },
    { id: 'mustache', name: '👨 Gentleman Mustache', emoji: '👨' },
    { id: 'clown-nose', name: '🤡 Clown Nose', emoji: '🤡' },
    { id: 'fox-ears', name: '🦊 Fox Ears', emoji: '🦊' },
    { id: 'panda-face', name: '🐼 Panda Mask', emoji: '🐼' },
    { id: 'lion-mane', name: '🦁 Lion Mane', emoji: '🦁' },
    { id: 'monkey-face', name: '🐵 Monkey Mask', emoji: '🐵' },

    // --- Funny Masks & Overlays (10 items) ---
    { id: 'mask', name: '🎭 Carnival Mask', emoji: '🎭' },
    { id: 'gas-mask', name: '😷 Gas Mask', emoji: '😷' },
    { id: 'skull-mask', name: '💀 Skull Face', emoji: '💀' },
    { id: 'alien-face', name: '👽 Alien Face', emoji: '👽' },
    { id: 'robot-face', name: '🤖 Robot Mask', emoji: '🤖' },
    { id: 'pumpkin-head', name: '🎃 Pumpkin Head', emoji: '🎃' },
    { id: 'ghost-mask', name: '👻 Ghost Mask', emoji: '👻' },
    { id: 'star-crown', name: '✨ Star Aura', emoji: '✨' },
    { id: 'butterfly-crown', name: '🦋 Butterfly Tiara', emoji: '🦋' },
    { id: 'heart-aura', name: '💖 Heart Aura', emoji: '💖' }
];

// Generate 300 Snapchat filters/lenses procedurally
const SNAP_LENSES = [];
function generateLenses() {
    if (SNAP_LENSES.length > 0) return;
    
    // Core custom categories
    const categories = ["Desert", "Aqua", "Lava", "Mint", "Grape", "Peach", "Retro", "Neon", "Cyber", "Forest", "Glow", "Vintage", "Solar", "Ocean", "Sunset", "Sunrise", "Polar", "Cosmic", "Galaxy", "Nebula"];
    const adjectives = ["Soft", "Deep", "Vibrant", "Dark", "Bright", "Warm", "Cool", "Electric", "Wild", "Magic", "Psychedelic", "Faded", "Glossy", "Matte", "Pastel", "Golden", "Silver", "Neon", "Spectral", "Dreamy"];
    
    // Add standard preset styles first
    SNAP_LENSES.push({ id: 'none', name: 'Normal / None', css: '' });
    SNAP_LENSES.push({ id: 'beauty-fair', name: '✨ Fair Glow (गोरा रंग)', css: 'brightness(1.25) contrast(0.95) saturate(1.05)' });
    SNAP_LENSES.push({ id: 'beauty-bright', name: '💖 Super Bright (अल्ट्रा गोरा)', css: 'brightness(1.4) contrast(0.9) saturate(1.1)' });
    SNAP_LENSES.push({ id: 'beauty-tan', name: '☀️ Sun Tan Look (गहू वर्ण)', css: 'brightness(0.9) contrast(1.1) sepia(0.15) saturate(1.2)' });
    SNAP_LENSES.push({ id: 'beauty-angel', name: '👼 Angelic Smooth', css: 'brightness(1.15) contrast(0.9) saturate(0.95) blur(0.3px)' });
    SNAP_LENSES.push({ id: 'beauty-gold', name: '💛 Golden Shine', css: 'sepia(0.2) brightness(1.2) contrast(1.05) saturate(1.3)' });
    SNAP_LENSES.push({ id: 'vintage', name: 'Vintage (Sepia)', css: 'sepia(0.6) contrast(1.1) brightness(0.9)' });
    SNAP_LENSES.push({ id: 'bw', name: 'Black & White', css: 'grayscale(1) contrast(1.2)' });
    SNAP_LENSES.push({ id: 'warm', name: 'Warm Sunshine', css: 'saturate(1.4) sepia(0.2) hue-rotate(-10deg)' });
    SNAP_LENSES.push({ id: 'cool', name: 'Cool Breeze', css: 'saturate(0.8) hue-rotate(180deg) brightness(1.05)' });
    SNAP_LENSES.push({ id: 'glow', name: 'Vibrant Glow', css: 'saturate(1.6) contrast(1.15) brightness(1.1)' });
    SNAP_LENSES.push({ id: 'neon', name: 'Neon Dream', css: 'hue-rotate(120deg) saturate(2) contrast(1.2)' });
    SNAP_LENSES.push({ id: 'invert', name: 'Color Invert', css: 'invert(0.8) contrast(1.1)' });
    SNAP_LENSES.push({ id: 'blur', name: 'Soft Focus', css: 'blur(2px) saturate(1.2)' });
    
    // Generate up to 300 lenses
    for (let i = 10; i <= 300; i++) {
        const hue = (i * 13) % 360;
        const sat = 100 + ((i * 11) % 120);
        const con = 90 + ((i * 8) % 50);
        const bri = 90 + ((i * 6) % 35);
        const sep = (i % 7 === 0) ? 40 : 0;
        const gray = (i % 13 === 0) ? 90 : 0;
        
        let filterString = `hue-rotate(${hue}deg) saturate(${sat}%) contrast(${con}%) brightness(${bri}%)`;
        if (sep > 0) filterString += ` sepia(${sep}%)`;
        if (gray > 0) filterString += ` grayscale(${gray}%)`;
        
        const adj = adjectives[i % adjectives.length];
        const cat = categories[i % categories.length];
        
        SNAP_LENSES.push({
            id: `lens-${i}`,
            name: `${adj} ${cat} #${i}`,
            css: filterString
        });
    }
}

function startCanvasDrawLoop() {
    const canvas = document.getElementById('snap-camera-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const video = document.getElementById('snap-webcam-preview');
    
    function drawFrame() {
        if (!localCameraStream || video.paused || video.ended) {
            canvasAnimationId = null;
            return;
        }
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // 1. Apply selected CSS lens color filters to the feed frame
        const selectedLens = SNAP_LENSES.find(l => l.id === selectedSnapFilter);
        ctx.filter = selectedLens ? selectedLens.css : 'none';
        
        // Draw raw video webcam frames
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // 2. Draw AR Mask Emoji overlay (Reset filter first so colors match!)
        ctx.filter = 'none';
        if (selectedARProp !== 'none' && selectedARPropEmoji !== '') {
            ctx.save();
            ctx.font = `${80 * propScale}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            // Draw vector emoji onto canvas center adjusted with custom offsets
            ctx.fillText(selectedARPropEmoji, (canvas.width / 2) + propXOffset, (canvas.height / 2) + propYOffset);
            ctx.restore();
        }
        
        canvasAnimationId = requestAnimationFrame(drawFrame);
    }
    
    if (canvasAnimationId) cancelAnimationFrame(canvasAnimationId);
    canvasAnimationId = requestAnimationFrame(drawFrame);
}

function selectARProp(propId) {
    selectedARProp = propId;
    const propObj = AR_PROPS.find(p => p.id === propId);
    selectedARPropEmoji = propObj ? propObj.emoji : '';
    
    // Update active class in props carousel
    const items = document.querySelectorAll('.snap-prop-item');
    items.forEach((item, idx) => {
        const pObj = AR_PROPS[idx];
        if (pObj && pObj.id === propId) {
            item.classList.add('active');
            item.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        } else {
            item.classList.remove('active');
        }
    });

    // Display / Hide controls overlay
    const adjustControls = document.getElementById('snap-adjust-controls');
    if (propId !== 'none') {
        adjustControls.style.display = 'flex';
    } else {
        adjustControls.style.display = 'none';
    }
}

function adjustARProp(action) {
    if (selectedARProp === 'none') return;
    
    const step = 8;
    const scaleStep = 0.08;
    
    if (action === 'up') propYOffset -= step;
    else if (action === 'down') propYOffset += step;
    else if (action === 'left') propXOffset -= step;
    else if (action === 'right') propXOffset += step;
    else if (action === 'scaleUp') propScale = Math.min(2.5, propScale + scaleStep);
    else if (action === 'scaleDown') propScale = Math.max(0.4, propScale - scaleStep);
    else if (action === 'reset') {
        propXOffset = 0;
        propYOffset = -40;
        propScale = 1.0;
    }
}

function openSnapchatCamera() {
    if (!activeUsername) {
        alert("Please select a user to send the snap to first!");
        return;
    }
    
    generateLenses();
    
    const modal = document.getElementById('snapchat-camera-modal');
    if (modal) modal.style.display = 'flex';
    
    // Reset canvas display & preview controls
    const canvasEl = document.getElementById('snap-camera-canvas');
    if (canvasEl) canvasEl.style.display = 'block';
    
    const recordedPreview = document.getElementById('snap-recorded-preview');
    if (recordedPreview) recordedPreview.style.display = 'none';
    
    // Populate lenses carousel
    const carousel = document.getElementById('snap-lenses-carousel');
    if (carousel) {
        carousel.innerHTML = '';
        SNAP_LENSES.forEach((lens, index) => {
            const item = document.createElement('div');
            item.className = `snap-lens-item ${lens.id === 'none' ? 'active' : ''}`;
            item.style.filter = lens.css;
            
            let labelName = lens.name.split(' ')[0];
            if (lens.id.startsWith('beauty-')) {
                labelName = lens.name;
            }
            
            item.innerHTML = `<span style="font-size:8px; line-height: 1.1; overflow:hidden; text-overflow:ellipsis; display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical; width:100%; font-weight: bold; white-space: normal;">${labelName}</span>`;
            item.onclick = (e) => {
                e.stopPropagation();
                selectSnapLens(lens.id);
            };
            carousel.appendChild(item);
        });
    }
    
    // Populate props carousel
    const propsCarousel = document.getElementById('snap-props-carousel');
    if (propsCarousel) {
        propsCarousel.innerHTML = '';
        AR_PROPS.forEach((prop, index) => {
            const item = document.createElement('div');
            item.className = `snap-prop-item ${prop.id === 'none' ? 'active' : ''}`;
            item.innerHTML = `<span style="font-size:16px; margin-bottom: 2px;">${prop.emoji || '❌'}</span><span style="font-size:7px; font-weight:bold; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; width:100%;">${prop.name}</span>`;
            item.onclick = (e) => {
                e.stopPropagation();
                selectARProp(prop.id);
            };
            propsCarousel.appendChild(item);
        });
    }
    
    // Start webcam preview with video/audio constraints
    const constraints = {
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: true
    };
    
    navigator.mediaDevices.getUserMedia(constraints)
    .then(stream => {
        setupWebcamStream(stream);
    })
    .catch(err => {
        console.warn("Retrying webcam access without audio:", err);
        // Fall back to video-only if microphone access fails or is denied
        navigator.mediaDevices.getUserMedia({
            video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } }
        })
        .then(stream => {
            setupWebcamStream(stream);
        })
        .catch(err2 => {
            console.error("Webcam access failed completely:", err2);
            alert("Unable to access camera. Please check permissions! (कैमरा एक्सेस की अनुमति दें)");
            closeSnapchatCamera();
        });
    });
}

function setupWebcamStream(stream) {
    localCameraStream = stream;
    const previewEl = document.getElementById('snap-webcam-preview');
    if (!previewEl) return;
    
    previewEl.srcObject = stream;
    previewEl.muted = true;
    
    previewEl.onloadedmetadata = () => {
        previewEl.play()
        .then(() => {
            startCanvasDrawLoop();
        })
        .catch(e => {
            console.warn("Forcing draw loop due to autoplay play() rejection:", e);
            startCanvasDrawLoop();
        });
    };
    
    // Fallback if metadata event is delayed
    setTimeout(() => {
        if (previewEl.paused) {
            previewEl.play().then(() => startCanvasDrawLoop()).catch(() => startCanvasDrawLoop());
        }
    }, 500);
}

function closeSnapchatCamera() {
    const modal = document.getElementById('snapchat-camera-modal');
    if (modal) modal.style.display = 'none';
    
    if (canvasAnimationId) {
        cancelAnimationFrame(canvasAnimationId);
        canvasAnimationId = null;
    }
    
    // Stop recording timer
    if (recordingCountdownInterval) {
        clearInterval(recordingCountdownInterval);
        recordingCountdownInterval = null;
    }
    
    // Stop webcam tracks
    if (localCameraStream) {
        localCameraStream.getTracks().forEach(track => track.stop());
        localCameraStream = null;
    }
    
    // Stop recorded preview
    const recordedPreview = document.getElementById('snap-recorded-preview');
    if (recordedPreview) {
        recordedPreview.pause();
        recordedPreview.src = '';
    }
    
    // Hide controls & reset prop selections
    document.getElementById('snap-adjust-controls').style.display = 'none';
    selectedARProp = 'none';
    selectedARPropEmoji = '';
    propXOffset = 0;
    propYOffset = -40;
    propScale = 1.0;
    
    retakeSnap();
}

function selectSnapLens(lensId) {
    selectedSnapFilter = lensId;
    
    // Update active class in lenses carousel
    const items = document.querySelectorAll('.snap-lens-item');
    items.forEach((item, idx) => {
        const lensObj = SNAP_LENSES[idx];
        if (lensObj && lensObj.id === lensId) {
            item.classList.add('active');
            item.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        } else {
            item.classList.remove('active');
        }
    });
}

function toggleSnapRecording() {
    const canvas = document.getElementById('snap-camera-canvas');
    if (!canvas || !localCameraStream) return;
    
    // Capture real-time frames from drawing canvas (30 FPS)
    const canvasStream = canvas.captureStream(30);
    
    // Add microphone audio tracks to the canvas video stream
    const audioTracks = localCameraStream.getAudioTracks();
    if (audioTracks.length > 0) {
        canvasStream.addTrack(audioTracks[0]);
    }
    
    recordedChunks = [];
    let options = { mimeType: 'video/webm;codecs=vp9,opus' };
    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = { mimeType: 'video/webm;codecs=vp8,opus' };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options = { mimeType: 'video/mp4' };
        }
    }
    
    try {
        mediaRecorderInstance = new MediaRecorder(canvasStream, options);
    } catch (e) {
        mediaRecorderInstance = new MediaRecorder(canvasStream);
    }
    
    mediaRecorderInstance.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
            recordedChunks.push(event.data);
        }
    };
    
    mediaRecorderInstance.onstop = () => {
        recordedSnapBlob = new Blob(recordedChunks, { type: mediaRecorderInstance.mimeType });
        
        // Hide canvas preview and show recorded video preview
        const canvasPreview = document.getElementById('snap-camera-canvas');
        const recordedPreview = document.getElementById('snap-recorded-preview');
        canvasPreview.style.display = 'none';
        recordedPreview.style.display = 'block';
        recordedPreview.src = URL.createObjectURL(recordedSnapBlob);
        recordedPreview.play().catch(e => console.debug("Preview video error:", e));
        
        // Show send/retake actions, hide record button
        document.getElementById('snap-record-btn').style.display = 'none';
        document.getElementById('snap-send-btn').style.display = 'block';
        document.getElementById('snap-retake-btn').style.display = 'block';
        
        // Hide lenses carousel & controls during preview
        document.getElementById('snap-lenses-carousel').style.display = 'none';
        document.getElementById('snap-props-carousel').style.display = 'none';
        document.getElementById('snap-adjust-controls').style.display = 'none';
        document.getElementById('snap-countdown-overlay').style.display = 'none';
    };
    
    // Start recording
    mediaRecorderInstance.start();
    
    // Start countdown timer overlay UI
    const countdownOverlay = document.getElementById('snap-countdown-overlay');
    const countdownProgress = document.getElementById('countdown-progress-circle');
    const countdownText = document.getElementById('countdown-timer-text');
    countdownOverlay.style.display = 'flex';
    
    let timeRemaining = SNAP_RECORDING_DURATION;
    const intervalTick = 50;
    
    recordingCountdownInterval = setInterval(() => {
        timeRemaining -= intervalTick;
        if (timeRemaining <= 0) {
            timeRemaining = 0;
            clearInterval(recordingCountdownInterval);
            recordingCountdownInterval = null;
            if (mediaRecorderInstance && mediaRecorderInstance.state !== 'inactive') {
                mediaRecorderInstance.stop();
            }
        }
        
        // Update countdown text & stroke offset
        countdownText.textContent = `${(timeRemaining / 1000).toFixed(1)}s`;
        const percentage = (timeRemaining / SNAP_RECORDING_DURATION) * 100;
        countdownProgress.setAttribute('stroke-dasharray', `${percentage}, 100`);
    }, intervalTick);
    
    document.getElementById('snap-record-btn').textContent = '⏹️ Recording...';
    document.getElementById('snap-record-btn').disabled = true;
}

function retakeSnap() {
    if (recordingCountdownInterval) {
        clearInterval(recordingCountdownInterval);
        recordingCountdownInterval = null;
    }
    
    // Hide previews, clear fields
    const canvasPreview = document.getElementById('snap-camera-canvas');
    const recordedPreview = document.getElementById('snap-recorded-preview');
    canvasPreview.style.display = 'block';
    recordedPreview.style.display = 'none';
    recordedPreview.pause();
    recordedPreview.src = '';
    
    document.getElementById('snap-record-btn').style.display = 'block';
    document.getElementById('snap-record-btn').disabled = false;
    document.getElementById('snap-record-btn').textContent = '🔴 Record 5s Snap';
    document.getElementById('snap-send-btn').style.display = 'none';
    document.getElementById('snap-retake-btn').style.display = 'none';
    
    document.getElementById('snap-lenses-carousel').style.display = 'flex';
    document.getElementById('snap-props-carousel').style.display = 'flex';
    if (selectedARProp !== 'none') {
        document.getElementById('snap-adjust-controls').style.display = 'flex';
    }
    document.getElementById('snap-countdown-overlay').style.display = 'none';
    recordedSnapBlob = null;
    
    if (localCameraStream && !canvasAnimationId) {
        startCanvasDrawLoop();
    }
}

function sendSnapToActiveThread() {
    if (!recordedSnapBlob || !activeUsername) return;
    
    const sendBtn = document.getElementById('snap-send-btn');
    sendBtn.disabled = true;
    sendBtn.textContent = 'Sending snap...';
    
    const csrfToken = getCookie('csrftoken');
    const formData = new FormData();
    // Convert WebM recorded snap to a file
    const file = new File([recordedSnapBlob], `snap_${Date.now()}.webm`, { type: recordedSnapBlob.type });
    formData.append('image', file); 
    formData.append('is_snap', 'true');
    
    // Save chosen lens & prop settings in content field so client plays it with the exact selected style
    const selectedLens = SNAP_LENSES.find(l => l.id === selectedSnapFilter);
    const filterConfig = {
        filterId: selectedSnapFilter,
        css: selectedLens ? selectedLens.css : '',
        propId: selectedARProp,
        propEmoji: selectedARPropEmoji,
        propX: propXOffset,
        propY: propYOffset,
        propScale: propScale
    };
    formData.append('content', JSON.stringify(filterConfig));

    fetch(`/api/chat/messages/${activeUsername}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(res => {
        if (res.ok) {
            closeSnapchatCamera();
            loadMessages();
        } else {
            alert('Failed to send snap message.');
            sendBtn.disabled = false;
            sendBtn.textContent = '✉️ Send Snap';
        }
    })
    .catch(err => {
        console.error('Error uploading snap:', err);
        alert('Upload failed.');
        sendBtn.disabled = false;
        sendBtn.textContent = '✉️ Send Snap';
    });
}

function playSnapMessage(msgId, videoUrl, filterConfigJsonStr) {
    let filterCss = '';
    let propEmoji = '';
    let propX = 0;
    let propY = -40;
    let propScale = 1.0;
    try {
        const config = JSON.parse(decodeURIComponent(filterConfigJsonStr));
        filterCss = config.css || '';
        propEmoji = config.propEmoji || '';
        propX = config.propX || 0;
        propY = config.propY || -40;
        propScale = config.propScale || 1.0;
    } catch(e) {}
    
    // Create Snap Player modal on the fly
    let player = document.getElementById('snap-player-overlay');
    if (!player) {
        player = document.createElement('div');
        player.id = 'snap-player-overlay';
        player.style.cssText = `
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background-color: #000;
            z-index: 2000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        document.body.appendChild(player);
    }
    
    player.innerHTML = `
        <div style="position: relative; width: 100%; max-width: 420px; height: 100vh; display: flex; align-items: center; justify-content: center;">
            <video src="${videoUrl}" autoplay playsinline style="width: 100%; height: 100%; object-fit: contain; filter: ${filterCss};" id="snap-play-video"></video>
            
            <!-- Prop Overlay Badge during playback -->
            ${propEmoji ? `
                <div style="position: absolute; pointer-events: none; text-align: center; font-size: ${80 * propScale}px; transform: translate(${propX}px, ${propY}px); z-index: 2010; color: white;">
                    ${propEmoji}
                </div>
            ` : ''}
            
            <!-- Floating Timer Indicator -->
            <div style="position: absolute; top: 20px; right: 20px; background-color: rgba(0,0,0,0.6); padding: 8px 16px; border-radius: 20px; font-weight: 700; color: #fffc00; font-size: 13px;" id="snap-play-timer">
                ⏱️ 5.0s
            </div>
        </div>
    `;
    
    player.style.display = 'flex';
    
    // Start 5 seconds play countdown
    const timerText = document.getElementById('snap-play-timer');
    let timeRemaining = 5000;
    const intervalTick = 100;
    
    const playTimerInterval = setInterval(() => {
        timeRemaining -= intervalTick;
        if (timeRemaining <= 0) {
            timeRemaining = 0;
            clearInterval(playTimerInterval);
            
            // Close player
            player.style.display = 'none';
            const vid = document.getElementById('snap-play-video');
            if (vid) vid.pause();
            
            // Delete snap instantly from server so it disappears forever
            const csrfToken = getCookie('csrftoken');
            fetch(`/api/chat/messages/delete/${msgId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
            .then(() => {
                chatMessagesList = []; // force reload
                loadMessages();
            });
        }
        
        timerText.textContent = `⏱️ ${(timeRemaining / 1000).toFixed(1)}s`;
    }, intervalTick);
}
