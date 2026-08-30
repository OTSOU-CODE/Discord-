// Public Wall Logic for TrustWall
document.addEventListener('DOMContentLoaded', () => {
    loadWall();
});

function loadWall() {
    try {
        const slug = window.TrustWallStorage ? window.TrustWallStorage.getSlugFromUrl() : 'demo-store';
        const wall = window.TrustWallStorage ? window.TrustWallStorage.getWallBySlug(slug) : null;

        const wallContainer = document.getElementById('wallContainer');
        if (!wall) {
            if (wallContainer) {
                wallContainer.innerHTML = `
                    <div style="text-align: center; padding: 4rem 1rem; background: var(--white); border-radius: var(--radius); margin-top: 2rem;">
                        <h1 style="margin-bottom: 1rem; color: var(--dark);">الجدار غير موجود 🔍</h1>
                        <p style="color: var(--gray); margin-bottom: 1.5rem;">تأكد من صحة الرابط أو أنشئ جدارك الخاص الآن</p>
                        <a href="index.html" class="btn-primary">العودة للرئيسية</a>
                    </div>
                `;
            }
            return;
        }

        const testimonials = window.TrustWallStorage ? window.TrustWallStorage.getWallTestimonials(wall.id, 'approved') : [];

        // Set Title & Description
        const titleEl = document.getElementById('wallTitle');
        const descEl = document.getElementById('wallDesc');
        const headerEl = document.querySelector('.wall-header');

        if (titleEl) titleEl.textContent = wall.title;
        if (descEl) descEl.textContent = wall.description || '';
        if (headerEl) headerEl.style.borderTop = `4px solid ${wall.color || 'var(--primary)'}`;

        const grid = document.getElementById('testimonialsGrid');
        if (!grid) return;

        if (testimonials.length === 0) {
            grid.innerHTML = '<p style="text-align:center; color: var(--gray); grid-column: 1/-1; padding: 3rem 0;">لا توجد شهادات معتمدة بعد في هذا الجدار</p>';
            return;
        }

        grid.innerHTML = testimonials.map(t => {
            const stars = '⭐'.repeat(t.rating || 5);
            const avatarHtml = t.author_image
                ? `<img src="${t.author_image}" class="author-avatar" style="object-fit:cover;" alt="${escapeHtml(t.author_name)}">`
                : `<div class="author-avatar">${escapeHtml(t.author_name.charAt(0) || '👤')}</div>`;

            return `
                <div class="testimonial-card" style="border-top: 3px solid ${wall.color || 'var(--primary)'}">
                    <div class="stars">${stars}</div>
                    <p class="testimonial-text">"${escapeHtml(t.content)}"</p>
                    <div class="testimonial-author">
                        ${avatarHtml}
                        <div>
                            <div class="author-name">${escapeHtml(t.author_name)}</div>
                            <div class="author-role">${new Date(t.created_at || Date.now()).toLocaleDateString('ar-SA')}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Error loading wall:', err);
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
