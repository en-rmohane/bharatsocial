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
                if (msg.image) {
                    mediaHtml = `<img src="${msg.image}" class="message-image" alt="Shared image" onclick="window.open('${msg.image}')">`;
                }

                // Decrypt message content if E2EE
                let displayMsg = msg.content || "";
                if (displayMsg.startsWith(E2EE_PREFIX) && typeof currentLoggedInUsername !== 'undefined') {
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
