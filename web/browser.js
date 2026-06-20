/**
 * Tux Wallpaper - Browser UI
 *
 * JavaScript for the wallpaper browser and management UI.
 * Communicates with the local Tux Wallpaper API (port 18421).
 */

const API_BASE = 'http://127.0.0.1:18421/api';

// Application state
const state = {
    wallpapers: [],
    favorites: [],
    localWallpapers: [],
    currentPreview: null,
    settings: {
        loop: true,
        mute: true,
        hwdec: 'auto',
        speed: 1.0,
        serverUrl: 'http://localhost:18420',
    },
    playbackState: {
        state: 'stopped',
        wallpaperId: null,
        title: null,
    },
};

// ============================================================================
// API Client
// ============================================================================

async function apiGet(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

async function apiPost(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

async function apiPatch(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

async function apiDelete(path) {
    const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

async function apiPut(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

// ============================================================================
// UI Rendering
// ============================================================================

function renderWallpaperGrid(wallpapers, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (wallpapers.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No wallpapers found.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = wallpapers.map(wp => `
        <div class="wallpaper-card" onclick="app.showPreview(${wp.id})">
            <img
                class="wallpaper-thumb"
                src="${wp.thumbnail_url || 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 9%22><rect fill=%22%230f3460%22 width=%2216%22 height=%229%22/></svg>'}"
                alt="${wp.title}"
                onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 9%22><rect fill=%22%230f3460%22 width=%2216%22 height=%229%22/></svg>'"
            >
            <div class="wallpaper-info">
                <div class="wallpaper-title">${escapeHtml(wp.title)}</div>
                <div class="wallpaper-meta">
                    ${wp.duration ? `<span>⏱ ${formatDuration(wp.duration)}</span>` : ''}
                    ${wp.width && wp.height ? `<span>${wp.width}×${wp.height}</span>` : ''}
                    ${wp.is_favorite ? '<span>♡</span>' : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDuration(seconds) {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const view = document.getElementById(`view-${viewName}`);
    const btn = document.querySelector(`[data-view="${viewName}"]`);

    if (view) view.classList.add('active');
    if (btn) btn.classList.add('active');

    // Load view-specific data
    if (viewName === 'favorites') {
        loadFavorites();
    } else if (viewName === 'local') {
        loadLocalWallpapers();
    } else if (viewName === 'settings') {
        loadSettings();
    }
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function updatePlaybackIndicator() {
    const indicator = document.getElementById('playback-indicator');
    const title = document.getElementById('now-playing-title');

    if (state.playbackState.state === 'playing' && state.playbackState.title) {
        indicator.classList.remove('hidden');
        title.textContent = state.playbackState.title;
    } else {
        indicator.classList.add('hidden');
    }
}

// ============================================================================
// Data Loading
// ============================================================================

async function loadWallpapers() {
    const grid = document.getElementById('wallpaper-grid');
    const loading = document.getElementById('loading-indicator');
    const empty = document.getElementById('empty-state');

    loading.classList.remove('hidden');
    grid.innerHTML = '';
    empty.classList.add('hidden');

    try {
        const wallpapers = await apiGet('/wallpapers');
        state.wallpapers = wallpapers;
        renderWallpaperGrid(wallpapers, 'wallpaper-grid');

        if (wallpapers.length === 0) {
            empty.classList.remove('hidden');
        }
    } catch (err) {
        console.error('Failed to load wallpapers:', err);
        showToast('Failed to load wallpapers: ' + err.message, 'error');
    } finally {
        loading.classList.add('hidden');
    }
}

async function loadFavorites() {
    try {
        const favorites = await apiGet('/wallpapers?favorite=true');
        state.favorites = favorites;
        renderWallpaperGrid(favorites, 'favorites-grid');
    } catch (err) {
        console.error('Failed to load favorites:', err);
        showToast('Failed to load favorites', 'error');
    }
}

async function loadLocalWallpapers() {
    try {
        const local = await apiGet('/wallpapers?source=local');
        state.localWallpapers = local;
        renderWallpaperGrid(local, 'local-grid');
    } catch (err) {
        console.error('Failed to load local wallpapers:', err);
        showToast('Failed to load local wallpapers', 'error');
    }
}

async function loadSettings() {
    try {
        const playerSettings = await apiGet('/settings/player');
        state.settings = {
            ...state.settings,
            loop: playerSettings.loop,
            mute: playerSettings.mute,
            hwdec: playerSettings.hwdec,
            speed: playerSettings.speed,
        };

        document.getElementById('setting-loop').checked = state.settings.loop;
        document.getElementById('setting-mute').checked = state.settings.mute;
        document.getElementById('setting-hwdec').value = state.settings.hwdec;
        document.getElementById('setting-speed').value = state.settings.speed;
        document.getElementById('speed-value').textContent = state.settings.speed.toFixed(1);
        document.getElementById('setting-server-url').value = state.settings.serverUrl;
    } catch (err) {
        console.error('Failed to load settings:', err);
    }
}

async function loadPlaybackState() {
    try {
        const playback = await apiGet('/playback/state');
        state.playbackState = playback;
        updatePlaybackIndicator();
    } catch (err) {
        // Ignore - player may not be running
    }
}

// ============================================================================
// Actions
// ============================================================================

async function showPreview(wallpaperId) {
    const wallpaper = state.wallpapers.find(w => w.id === wallpaperId)
        || state.localWallpapers.find(w => w.id === wallpaperId)
        || state.favorites.find(w => w.id === wallpaperId);

    if (!wallpaper) {
        try {
            const wp = await apiGet(`/wallpapers/${wallpaperId}`);
            state.currentPreview = wp;
            wallpaper = wp;
        } catch {
            showToast('Wallpaper not found', 'error');
            return;
        }
    }

    state.currentPreview = wallpaper;

    document.getElementById('preview-title').textContent = wallpaper.title;
    document.getElementById('preview-description').textContent =
        wallpaper.description || 'No description';
    document.getElementById('preview-duration').textContent =
        wallpaper.duration ? `⏱ ${formatDuration(wallpaper.duration)}` : '';
    document.getElementById('preview-resolution').textContent =
        wallpaper.width && wallpaper.height ? `${wallpaper.width}×${wallpaper.height}` : '';

    // Tags
    const tagsContainer = document.getElementById('preview-tags');
    tagsContainer.innerHTML = (wallpaper.tags || []).map(tag =>
        `<span class="tag">${escapeHtml(tag)}</span>`
    ).join('');

    // Favorite button
    const favBtn = document.getElementById('preview-favorite-btn');
    favBtn.textContent = wallpaper.is_favorite ? '♡ Favorited' : '♡ Favorite';
    favBtn.classList.toggle('favorited', wallpaper.is_favorite);

    // Show modal
    document.getElementById('preview-modal').classList.remove('hidden');
}

function closePreview() {
    const modal = document.getElementById('preview-modal');
    const video = document.getElementById('preview-video');
    video.pause();
    modal.classList.add('hidden');
    state.currentPreview = null;
}

async function toggleFavorite() {
    if (!state.currentPreview) return;

    try {
        const updated = await apiPatch(
            `/wallpapers/${state.currentPreview.id}`,
            { is_favorite: !state.currentPreview.is_favorite }
        );

        state.currentPreview.is_favorite = updated.is_favorite;

        const favBtn = document.getElementById('preview-favorite-btn');
        favBtn.textContent = updated.is_favorite ? '♡ Favorited' : '♡ Favorite';
        favBtn.classList.toggle('favorited', updated.is_favorite);

        showToast(
            updated.is_favorite ? 'Added to favorites' : 'Removed from favorites'
        );
    } catch (err) {
        showToast('Failed to update favorite', 'error');
    }
}

async function playWallpaper() {
    if (!state.currentPreview) return;

    try {
        await apiPost(`/playback/wallpaper/${state.currentPreview.id}`, {});

        state.playbackState = {
            state: 'playing',
            wallpaperId: state.currentPreview.id,
            title: state.currentPreview.title,
        };
        updatePlaybackIndicator();

        showToast(`Now playing: ${state.currentPreview.title}`);
        closePreview();
    } catch (err) {
        showToast('Failed to play wallpaper: ' + err.message, 'error');
    }
}

async function saveSettings() {
    const settings = {
        loop: document.getElementById('setting-loop').checked,
        mute: document.getElementById('setting-mute').checked,
        hwdec: document.getElementById('setting-hwdec').value,
        speed: parseFloat(document.getElementById('setting-speed').value),
    };

    try {
        await apiPut('/settings/player', settings);
        state.settings = { ...state.settings, ...settings };
        showToast('Settings saved');
    } catch (err) {
        showToast('Failed to save settings: ' + err.message, 'error');
    }
}

async function addLocalVideo() {
    // Use file input to select video
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'video/*';

    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        // For now, just create a wallpaper entry without the file
        // TODO: Implement file upload to local storage
        showToast('Local video added (upload not yet implemented)');
    };

    input.click();
}

// ============================================================================
// Application Object
// ============================================================================

const app = {
    init() {
        // Set up navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const view = btn.dataset.view;
                if (view) showView(view);
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closePreview();
            }
        });

        // Speed slider: update displayed value in real-time
        const speedSlider = document.getElementById('setting-speed');
        if (speedSlider) {
            speedSlider.addEventListener('input', () => {
                const speedValue = document.getElementById('speed-value');
                if (speedValue) speedValue.textContent = parseFloat(speedSlider.value).toFixed(1);
            });
        }

        // Load initial data
        loadWallpapers();
        loadPlaybackState();

        // Refresh playback state periodically
        setInterval(loadPlaybackState, 5000);
    },

    showPreview,
    closePreview,
    toggleFavorite,
    playWallpaper,
    saveSettings,
    loadWallpapers,
    addLocalVideo,
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
