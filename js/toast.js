/**
 * TrustWall Apple-Style Toast Notification Manager
 */
(function(window) {
    class ToastManager {
        constructor() {
            this.container = null;
            this.init();
        }

        init() {
            if (document.getElementById('tw-toast-container')) {
                this.container = document.getElementById('tw-toast-container');
                return;
            }
            this.container = document.createElement('div');
            this.container.id = 'tw-toast-container';
            this.container.className = 'tw-toast-container';
            document.body.appendChild(this.container);
        }

        show(message, type = 'success', duration = 3500) {
            if (!this.container) this.init();

            const toast = document.createElement('div');
            toast.className = `tw-toast tw-toast--${type}`;

            const icons = {
                success: '✓',
                error: '✕',
                info: 'ℹ',
                copy: '📋'
            };

            toast.innerHTML = `
                <div class="tw-toast-icon">${icons[type] || '✨'}</div>
                <div class="tw-toast-message">${this.escapeHtml(message)}</div>
                <button class="tw-toast-close" aria-label="إغلاق">×</button>
            `;

            this.container.appendChild(toast);

            // Animate in
            requestAnimationFrame(() => {
                toast.classList.add('tw-toast--visible');
            });

            const closeBtn = toast.querySelector('.tw-toast-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.dismiss(toast));
            }

            if (duration > 0) {
                setTimeout(() => {
                    this.dismiss(toast);
                }, duration);
            }
        }

        dismiss(toast) {
            if (!toast || !toast.parentNode) return;
            toast.classList.remove('tw-toast--visible');
            toast.classList.add('tw-toast--hiding');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 350);
        }

        escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>"']/g, m => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
            }[m]));
        }
    }

    window.TrustWallToast = new ToastManager();
})(window);
