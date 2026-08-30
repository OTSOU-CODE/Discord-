// Embed Widget Logic for TrustWall
document.addEventListener('DOMContentLoaded', () => {
    loadEmbed();
});

function loadEmbed() {
    try {
        const slug = window.TrustWallStorage ? window.TrustWallStorage.getSlugFromUrl() : 'demo-store';
        const wall = window.TrustWallStorage ? window.TrustWallStorage.getWallBySlug(slug) : null;

        if (!wall) {
            const preview = document.getElementById('previewContainer');
            if (preview) {
                preview.innerHTML = '<p style="text-align:center; color: var(--gray);">الجدار غير موجود</p>';
            }
            return;
        }

        const testimonials = window.TrustWallStorage ? window.TrustWallStorage.getWallTestimonials(wall.id, 'approved') : [];
        const safeSlug = wall.slug.replace(/[^a-zA-Z0-9_-]/g, '');

        // Generate Standalone Embed Code
        const embedCode = `<!-- TrustWall Widget: ${escapeHtml(wall.title)} -->
<div id="trustwall-${safeSlug}"></div>
<script>
(function() {
    var container = document.getElementById('trustwall-${safeSlug}');
    if (!container) return;

    var style = document.createElement('style');
    style.textContent = \`
        .tw-widget { font-family: system-ui, -apple-system, sans-serif; max-width: 100%; direction: rtl; }
        .tw-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
        .tw-card { background: #ffffff; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-top: 3px solid ${wall.color || '#3b82f6'}; }
        .tw-stars { color: #f59e0b; margin-bottom: 0.5rem; font-size: 1rem; }
        .tw-text { font-size: 0.95rem; line-height: 1.6; margin-bottom: 1rem; color: #1e293b; }
        .tw-author { display: flex; align-items: center; gap: 0.75rem; }
        .tw-avatar { width: 36px; height: 36px; background: ${wall.color || '#3b82f6'}20; color: ${wall.color || '#3b82f6'}; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.9rem; }
        .tw-name { font-weight: 700; font-size: 0.9rem; color: #0f172a; }
    \`;
    document.head.appendChild(style);

    var data = ${JSON.stringify(testimonials.map(t => ({
        name: t.author_name,
        content: t.content,
        rating: t.rating || 5
    })))};

    var widget = document.createElement('div');
    widget.className = 'tw-widget';
    widget.innerHTML = '<div class="tw-grid">' + 
        data.map(function(t) {
            return '<div class="tw-card">' +
                '<div class="tw-stars">' + '⭐'.repeat(t.rating) + '</div>' +
                '<div class="tw-text">"' + t.content + '"</div>' +
                '<div class="tw-author">' +
                    '<div class="tw-avatar">' + (t.name ? t.name.charAt(0) : '👤') + '</div>' +
                    '<div class="tw-name">' + t.name + '</div>' +
                '</div>' +
            '</div>';
        }).join('') + 
    '</div>';
    container.appendChild(widget);
})();
<\/script>`;

        const codeArea = document.getElementById('embedCode');
        if (codeArea) codeArea.value = embedCode;

        // Live Preview
        const preview = document.getElementById('previewContainer');
        if (preview) {
            if (testimonials.length === 0) {
                preview.innerHTML = '<p style="text-align:center; color: var(--gray);">لا توجد شهادات معتمدة لعرضها في المعاينة</p>';
                return;
            }

            preview.innerHTML = testimonials.map(t => `
                <div class="testimonial-card" style="border-top: 3px solid ${wall.color || 'var(--primary)'}; margin-bottom: 1rem;">
                    <div class="stars">${'⭐'.repeat(t.rating || 5)}</div>
                    <p class="testimonial-text">"${escapeHtml(t.content)}"</p>
                    <div class="testimonial-author">
                        ${t.author_image ? `<img src="${t.author_image}" class="author-avatar" style="object-fit:cover;">` : `<div class="author-avatar">${escapeHtml(t.author_name.charAt(0) || '👤')}</div>`}
                        <div class="author-name">${escapeHtml(t.author_name)}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('Error loading embed:', err);
    }
}

function copyEmbed() {
    const textarea = document.getElementById('embedCode');
    if (!textarea) return;
    textarea.select();
    textarea.setSelectionRange(0, 99999);
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textarea.value).then(() => {
            alert('تم نسخ الكود بنجاح!');
        }).catch(() => {
            document.execCommand('copy');
            alert('تم نسخ الكود بنجاح!');
        });
    } else {
        document.execCommand('copy');
        alert('تم نسخ الكود بنجاح!');
    }
}

// Utility: HTML escaping
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, function(m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[m];
    });
}
