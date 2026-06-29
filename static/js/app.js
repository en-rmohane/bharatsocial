// --- Global Application Module ---

function initApp() {
    initTheme();
    initLanguage();
    initNotificationBadging();
    initUserActivityPing();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// --- CSRF Helper ---
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// --- Theme Switcher ---
function initTheme() {
    const themeToggle = document.getElementById('theme-toggle-btn');
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeButtonIcon(currentTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const activeTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeButtonIcon(newTheme);
        });
    }
}

function updateThemeButtonIcon(theme) {
    const iconSpan = document.getElementById('theme-toggle-icon');
    if (!iconSpan) return;
    if (theme === 'dark') {
        iconSpan.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 5a7 7 0 100 14 7 7 0 000-14z"/></svg>`;
    } else {
        iconSpan.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>`;
    }
}

// --- Hindi / English Localization (i18n) ---
const translations = {
    'en': {
        'nav_home': 'Home',
        'nav_search': 'Search',
        'nav_explore': 'Explore',
        'nav_reels': 'Reels',
        'nav_messages': 'Messages',
        'nav_notifications': 'Notifications',
        'nav_create': 'Create',
        'nav_profile': 'Profile',
        'nav_moderator': 'Moderator Dashboard',
        'nav_logout': 'Logout',
        'search_placeholder': 'Search users or hashtags...',
        'suggestions_title': 'Suggestions for you',
        'see_all': 'See All',
        'follow': 'Follow',
        'following': 'Following',
        'comment_placeholder': 'Add a comment...',
        'post_btn': 'Post',
        'likes': 'likes',
        'no_posts': 'No posts yet',
        'edit_profile_btn': 'Edit Profile',
        'posts_tab': 'Posts',
        'reels_tab': 'Reels',
        'saved_tab': 'Saved',
    },
    'hi': {
        'nav_home': 'मुख्य पृष्ठ',
        'nav_search': 'खोजें',
        'nav_explore': 'एक्सप्लोर',
        'nav_reels': 'रील्स',
        'nav_messages': 'संदेश',
        'nav_notifications': 'सूचनाएं',
        'nav_create': 'बनाएं',
        'nav_profile': 'प्रोफ़ाइल',
        'nav_moderator': 'मॉडरेटर डैशबोर्ड',
        'nav_logout': 'लॉगआउट',
        'search_placeholder': 'उपयोगकर्ता या हैशटैग खोजें...',
        'suggestions_title': 'आपके लिए सुझाव',
        'see_all': 'सभी देखें',
        'follow': 'फ़ॉलो करें',
        'following': 'फ़ॉलो कर रहे हैं',
        'comment_placeholder': 'एक टिप्पणी जोड़ें...',
        'post_btn': 'पोस्ट',
        'likes': 'पसंद',
        'no_posts': 'अभी तक कोई पोस्ट नहीं है',
        'edit_profile_btn': 'प्रोफ़ाइल संपादित करें',
        'posts_tab': 'पोस्ट',
        'reels_tab': 'रील्स',
        'saved_tab': 'सहेजे गए',
    }
};

function initLanguage() {
    const langSelector = document.getElementById('lang-switch-select');
    const savedLang = localStorage.getItem('lang') || 'en';
    
    if (langSelector) {
        langSelector.value = savedLang;
        langSelector.addEventListener('change', (e) => {
            const newLang = e.target.value;
            localStorage.setItem('lang', newLang);
            applyTranslations(newLang);
        });
    }
    
    applyTranslations(savedLang);
}

function applyTranslations(lang) {
    const dict = translations[lang] || translations['en'];
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (dict[key]) {
            if (element.tagName === 'INPUT' && element.getAttribute('type') === 'text') {
                element.placeholder = dict[key];
            } else {
                element.textContent = dict[key];
            }
        }
    });
}

// --- Notification Check Badges ---
function initNotificationBadging() {
    const notificationBadge = document.getElementById('notification-unread-count');
    const messageBadge = document.getElementById('message-unread-count');
    const mobileBadge = document.getElementById('mobile-notification-badge');
    if (!notificationBadge && !messageBadge && !mobileBadge) return;

    const checkCounts = () => {
        fetch('/api/notifications/unread-count/')
            .then(res => res.json())
            .then(data => {
                if (data.unread_count > 0) {
                    if (notificationBadge) {
                        notificationBadge.textContent = data.unread_count;
                        notificationBadge.style.display = 'flex';
                    }
                    if (mobileBadge) {
                        mobileBadge.textContent = data.unread_count;
                        mobileBadge.style.display = 'flex';
                    }
                } else {
                    if (notificationBadge) notificationBadge.style.display = 'none';
                    if (mobileBadge) mobileBadge.style.display = 'none';
                }
            })
            .catch(err => console.error('Error fetching unread counts:', err));
    };

    checkCounts();
    setInterval(checkCounts, 12000); // Check every 12 seconds
}

// --- Online Activity Status Ping ---
function initUserActivityPing() {
    // Ping to let backend know user is active (update cache entry for online check)
    // Send a message ping
    const pingActivity = () => {
        if (!document.hidden) {
            // Fetch notifications unread counts or similar page fetch acts as session renewal
            fetch('/api/notifications/unread-count/')
                .catch(err => console.debug('Offline or loading...'));
        }
    };
    
    pingActivity();
    setInterval(pingActivity, 20000); // Ping every 20 seconds
}
