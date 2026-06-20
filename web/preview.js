/**
 * Tux Wallpaper - Preview Module
 *
 * Handles wallpaper preview modal and video playback.
 * (Preview functionality is integrated into browser.js)
 */

(function() {
    'use strict';

    // Preview state
    let currentVideo = null;
    let previewEl = null;

    function init() {
        previewEl = document.getElementById('preview-modal');
        if (!previewEl) return;

        // Preview is handled by browser.js
        // This module can be extended for additional preview features
    }

    function formatDuration(seconds) {
        if (!seconds) return '';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function formatFileSize(bytes) {
        if (!bytes) return '';
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
