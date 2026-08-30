/**
 * TrustWall — Apple Widget Studio & Generator Logic
 */
let currentSlug = 'elite-store';
let activeTheme = 'light';
let activeLayout = 'grid';

document.addEventListener('DOMContentLoaded', () => {
    currentSlug = window.TrustWallStorage ? window.TrustWallStorage.getSlugFromUrl() : 'elite-store';
    populateWallSelector();
    setupConfigControls();
    updateEmbedCodeAndPreview();
});

function populateWallSelector() {
    const selector = document.getElementById('wallSelect');
    if (!selector || !window.TrustWallStorage) return;

    const walls = window.TrustWallStorage.getUserWalls();
    selector.innerHTML = walls.map(w => `
        <option value="${escapeHtml(w.slug)}" ${w.slug === currentSlug ? 'selected' : ''}>
            ${escapeHtml(w.title)} (${escapeHtml(w.slug)})
        </option>
    `).join('');

    selector.addEventListener('change', (e) => {
        currentSlug = e.target.value;
        updateEmbedCodeAndPreview();
    });
}

function setupConfigControls() {
    // Theme options
    const themePills = document.querySelectorAll('.embed-theme-btn');
    themePills.forEach(btn => {
        btn.addEventListener('click', () => {
            themePills.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeTheme = btn.getAttribute('data-theme') || 'light';
            updateEmbedCodeAndPreview();
        });
    });

    // Layout options
    const layoutPills = document.querySelectorAll('.embed-layout-btn');
    layoutPills.forEach(btn => {
        btn.addEventListener('click', () => {
            layoutPills.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeLayout = btn.getAttribute('data-layout') || 'grid';
            updateEmbedCodeAndPreview();
        });
    });
}

function updateEmbedCodeAndPreview() {
    const wall = window.TrustWallStorage ? window.TrustWallStorage.getWallBySlug(currentSlug) : null;
    const previewContainer = document.getElementById('embedPreviewCanvas');
    const codeArea = document.getElementById('embedCodeOutput');

    if (!wall) {
        if (previewContainer) previewContainer.innerHTML = '<p style="text-align:center; color:var(--text-secondary);">الجدار غير موجود</p>';
        return;
    }

    const testimonials = window.TrustWallStorage.getWallTestimonials(wall.id, 'approved');
    const safeSlug = wall.slug.replace(/[^a-zA-Z0-9_-]/g, '');

    // Theme Color Schemes
    const themeStyles = {
        light: {
            bg: '#ffffff',
            cardBg: '#ffffff',
            text: '#1d1d1f',
            subText: '#86868b',
            border: 'rgba(0, 0, 0, 0.08)',
            accent: wall.color || '#0071e3',
            stars: '#f5a623'
        },
        dark: {
            bg: '#0c0c0e',
            cardBg: '#18181b',
            text: '#f4f4f5',
            subText: '#a1a1aa',
            border: 'rgba(255, 255, 255, 0.12)',
            accent: wall.color || '#0071e3',
            stars: '#fbbf24'
        },
        glass: {
            bg: 'linear-gradient(135deg, #e0e7ff 0%, #f1f5f9 100%)',
            cardBg: 'rgba(255, 255, 255, 0.75)',
            text: '#1e293b',
            subText: '#64748b',
            border: 'rgba(255, 255, 255, 0.8)',
            accent: wall.color || '#0071e3',
            stars: '#f59e0b'
        },
        gold: {
            bg: '#1c1917',
            cardBg: '#292524',
            text: '#fef3c7',
            subText: '#d6d3d1',
            border: 'rgba(217, 119, 6, 0.3)',
            accent: '#f59e0b',
            stars: '#fbbf24'
        }
    }[activeTheme] || themeStyles.light;

    // Generate Clean Standalone Embed Script
    const snippet = `<!-- TrustWall Widget: ${escapeHtml(wall.title)} -->
<div id="trustwall-${safeSlug}"></div>
<script>
(function() {
    var container = document.getElementById('trustwall-${safeSlug}');
    if (!container) return;

    var style = document.createElement('style');
    style.textContent = \`
        .tw-embed-root { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Tajawal", sans-serif; direction: rtl; width: 100%; box-sizing: border-box; }
        .tw-embed-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.25rem; }
        .tw-embed-card { background: ${themeStyles.cardBg}; border-radius: 16px; padding: 1.5rem; border: 1px solid ${themeStyles.border}; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border-top: 3px solid ${themeStyles.accent}; display: flex; flex-direction: column; justify-content: space-between; }
        .tw-embed-stars { color: ${themeStyles.stars}; font-size: 1.1rem; margin-bottom: 0.75rem; letter-spacing: 0.05em; }
        .tw-embed-text { font-size: 0.95rem; line-height: 1.6; color: ${themeStyles.text}; margin-bottom: 1.25rem; }
        .tw-embed-author { display: flex; align-items: center; gap: 0.75rem; }
        .tw-embed-avatar { width: 40px; height: 40px; border-radius: 50%; background: ${themeStyles.accent}20; color: ${themeStyles.accent}; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.95rem; object-fit: cover; }
        .tw-embed-name { font-weight: 700; font-size: 0.9rem; color: ${themeStyles.text}; }
        .tw-embed-role { font-size: 0.75rem; color: ${themeStyles.subText}; }
    \`;
    document.head.appendChild(style);

    var testimonials = ${JSON.stringify(testimonials.map(t => ({
        name: t.author_name,
        role: t.author_role || 'عميل موثق',
        content: t.content,
        rating: t.rating || 5,
        image: t.author_image || ''
    })))};

    var root = document.createElement('div');
    root.className = 'tw-embed-root';
    root.innerHTML = '<div class="tw-embed-grid">' + 
        testimonials.map(function(t) {
            var avatar = t.image 
                ? '<img src="' + t.image + '" class="tw-embed-avatar" alt="' + t.name + '">'
                : '<div class="tw-embed-avatar">' + (t.name ? t.name.charAt(0) : '👤') + '</div>';
            return '<div class="tw-embed-card">' +
                '<div>' +
                    '<div class="tw-embed-stars">' + '⭐'.repeat(t.rating) + '</div>' +
                    '<p class="tw-embed-text">"' + t.content + '"</p>' +
                '</div>' +
                '<div class="tw-embed-author">' +
                    avatar +
                    '<div>' +
                        '<div class="tw-embed-name">' + t.name + '</div>' +
                        '<div class="tw-embed-role">' + t.role + '</div>' +
                    '</div>' +
                '</div>' +
            '</div>';
        }).join('') +
    '</div>';

    container.appendChild(root);
})();
<\/script>`;

    if (codeArea) codeArea.value = snippet;

    // Render Preview in Studio Canvas
    if (previewContainer) {
        previewContainer.style.background = themeStyles.bg;
        if (testimonials.length === 0) {
            previewContainer.innerHTML = `
                <p style="text-align:center; color:var(--text-secondary); padding:2rem 0;">
                    لا توجد شهادات معتمدة لعرضها في المعاينة
                </p>
            `;
            return;
        }

        previewContainer.innerHTML = `
            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:1.25rem;">
                ${testimonials.map(t => {
                    const avatar = t.author_image 
                        ? `<img src="${t.author_image}" style="width:40px; height:40px; border-radius:50%; object-fit:cover;" alt="${escapeHtml(t.author_name)}">`
                        : `<div style="width:40px; height:40px; border-radius:50%; background:${themeStyles.accent}20; color:${themeStyles.accent}; display:flex; align-items:center; justify-content:center; font-weight:700;">${escapeHtml(t.author_name.charAt(0) || '👤')}</div>`;

                    return `
                        <div style="background:${themeStyles.cardBg}; border:1px solid ${themeStyles.border}; border-top:3px solid ${themeStyles.accent}; border-radius:16px; padding:1.5rem; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 4px 20px rgba(0,0,0,0.06);">
                            <div>
                                <div style="color:${themeStyles.stars}; font-size:1.1rem; margin-bottom:0.75rem;">${'⭐'.repeat(t.rating || 5)}</div>
                                <p style="color:${themeStyles.text}; font-size:0.95rem; line-height:1.6; margin-bottom:1.25rem;">"${escapeHtml(t.content)}"</p>
                            </div>
                            <div style="display:flex; align-items:center; gap:0.75rem;">
                                ${avatar}
                                <div>
                                    <div style="font-weight:700; font-size:0.9rem; color:${themeStyles.text};">${escapeHtml(t.author_name)}</div>
                                    <div style="font-size:0.75rem; color:${themeStyles.subText};">${escapeHtml(t.author_role || 'عميل موثق')}</div>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }
}

function copyEmbedCode() {
    const textarea = document.getElementById('embedCodeOutput');
    if (!textarea) return;

    textarea.select();
    navigator.clipboard.writeText(textarea.value).then(() => {
        if (window.TrustWallToast) {
            window.TrustWallToast.show('تم نسخ كود التضمين بنجاح! 📋', 'copy', 2500);
        }
    }).catch(() => {
        document.execCommand('copy');
        if (window.TrustWallToast) {
            window.TrustWallToast.show('تم نسخ كود التضمين بنجاح! 📋', 'copy', 2500);
        }
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[m]));
}
