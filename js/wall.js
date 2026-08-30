/**
 * TrustWall — Apple Showcase Public Wall Logic
 */
let activeWall = null;
let currentFilter = 'all';
let currentSearch = '';

document.addEventListener('DOMContentLoaded', () => {
    loadWallData();
    setupWallControls();
});

function loadWallData() {
    try {
        const slug = window.TrustWallStorage ? window.TrustWallStorage.getSlugFromUrl() : 'elite-store';
        activeWall = window.TrustWallStorage ? window.TrustWallStorage.getWallBySlug(slug) : null;

        const container = document.getElementById('wallWrapper');
        if (!activeWall) {
            if (container) {
                container.innerHTML = `
                    <div style="text-align:center; padding:5rem 1.5rem; background:#fff; border-radius:var(--radius-lg); max-width:600px; margin:4rem auto; box-shadow:var(--shadow-card);">
                        <div style="font-size:3.5rem; margin-bottom:1rem;">🔍</div>
                        <h1 style="font-size:1.85rem; margin-bottom:0.75rem;">الجدار المطلوب غير موجود</h1>
                        <p style="color:var(--text-secondary); margin-bottom:2rem;">تأكد من صحة الرابط أو تفضل بإنشاء جدارك الخاص الآن</p>
                        <a href="index.html" class="btn-apple btn-apple-primary">العودة للرئيسية</a>
                    </div>
                `;
            }
            return;
        }

        // Apply Wall Accent Color
        document.documentElement.style.setProperty('--wall-accent-color', activeWall.color || '#0071e3');

        // Set Header info
        const titleEl = document.getElementById('wallTitle');
        const descEl = document.getElementById('wallDesc');
        const submitLink = document.getElementById('wallSubmitBtn');

        if (titleEl) titleEl.textContent = activeWall.title;
        if (descEl) descEl.textContent = activeWall.description || '';
        if (submitLink) submitLink.href = `submit.html?slug=${encodeURIComponent(activeWall.slug)}`;

        renderWallTestimonials();
    } catch (err) {
        console.error('Error loading wall:', err);
    }
}

function renderWallTestimonials() {
    if (!activeWall) return;

    let testimonials = window.TrustWallStorage.getWallTestimonials(activeWall.id, 'approved');

    // Apply Filter Pill
    if (currentFilter === '5') {
        testimonials = testimonials.filter(t => t.rating === 5);
    } else if (currentFilter === '4') {
        testimonials = testimonials.filter(t => t.rating === 4);
    } else if (currentFilter === 'photos') {
        testimonials = testimonials.filter(t => Boolean(t.author_image));
    }

    // Apply Search Query
    if (currentSearch.trim()) {
        const q = currentSearch.trim().toLowerCase();
        testimonials = testimonials.filter(t => 
            t.content.toLowerCase().includes(q) ||
            t.author_name.toLowerCase().includes(q) ||
            (t.author_role && t.author_role.toLowerCase().includes(q))
        );
    }

    const grid = document.getElementById('testimonialsGrid');
    if (!grid) return;

    if (testimonials.length === 0) {
        grid.innerHTML = `
            <div style="text-align:center; color:var(--text-secondary); grid-column:1/-1; padding:4rem 1rem; background:#fff; border-radius:var(--radius-lg); border:var(--glass-border);">
                <div style="font-size:2.5rem; margin-bottom:0.75rem;">💬</div>
                <h3 style="margin-bottom:0.5rem; color:var(--text-primary);">لا توجد شهادات مطابقة</h3>
                <p>كن أول من يشارك تجربته مع ${escapeHtml(activeWall.title)}!</p>
                <a href="submit.html?slug=${encodeURIComponent(activeWall.slug)}" class="btn-apple btn-apple-primary" style="margin-top:1.5rem;">✍️ أضف رأيك الآن</a>
            </div>
        `;
        return;
    }

    grid.innerHTML = testimonials.map(t => {
        const stars = '⭐'.repeat(t.rating || 5);
        const avatarHtml = t.author_image
            ? `<img src="${t.author_image}" class="public-t-avatar" alt="${escapeHtml(t.author_name)}">`
            : `<div class="public-t-avatar-initial">${escapeHtml(t.author_name.charAt(0) || '👤')}</div>`;

        return `
            <div class="public-t-card">
                <div>
                    <div class="public-t-stars">${stars}</div>
                    <p class="public-t-content">"${escapeHtml(t.content)}"</p>
                </div>

                <div class="public-t-footer">
                    ${avatarHtml}
                    <div class="public-t-info">
                        <div class="public-t-name">
                            ${escapeHtml(t.author_name)}
                            ${t.verified ? '<span class="tw-verified-badge" title="عميل موثق">✓</span>' : ''}
                        </div>
                        <div class="public-t-meta">
                            ${escapeHtml(t.author_role || 'عميل موثق')} • ${new Date(t.created_at || Date.now()).toLocaleDateString('ar-SA')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function setupWallControls() {
    // Filter Pills
    const pills = document.querySelectorAll('.wall-filter-pill');
    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            pills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            currentFilter = pill.getAttribute('data-filter') || 'all';
            renderWallTestimonials();
        });
    });

    // Search Input
    const searchInput = document.getElementById('wallSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value;
            renderWallTestimonials();
        });
    }

    // Share Wall Button
    const shareBtn = document.getElementById('shareWallBtn');
    if (shareBtn) {
        shareBtn.addEventListener('click', () => {
            const url = window.location.href;
            if (navigator.share) {
                navigator.share({
                    title: activeWall ? activeWall.title : 'TrustWall',
                    text: activeWall ? activeWall.description : 'شهادات العملاء',
                    url: url
                }).catch(() => {});
            } else {
                navigator.clipboard.writeText(url).then(() => {
                    if (window.TrustWallToast) {
                        window.TrustWallToast.show('تم نسخ رابط الجدار للمشاركة! 📋', 'copy');
                    }
                });
            }
        });
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[m]));
}
