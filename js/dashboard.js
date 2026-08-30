/**
 * TrustWall — Apple macOS-Grade Dashboard Manager
 */
let currentWallId = null;
let currentFilterStatus = 'all';

// Auth check
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || 'null');

if (!token && !user) {
    window.location.href = 'login.html';
}

document.addEventListener('DOMContentLoaded', () => {
    // Show user info
    const userNameEl = document.getElementById('userName');
    if (userNameEl && user && user.name) {
        userNameEl.textContent = `مرحباً، ${user.name}`;
    }

    renderAnalytics();
    loadWalls();
    setupSearch();
    setupCreateForm();
    setupBackupTools();
});

// Render Analytics Cards
function renderAnalytics() {
    if (!window.TrustWallStorage) return;
    const analytics = window.TrustWallStorage.getAnalytics();

    const statWalls = document.getElementById('statTotalWalls');
    const statReviews = document.getElementById('statTotalReviews');
    const statPending = document.getElementById('statPendingReviews');
    const statRating = document.getElementById('statAvgRating');

    if (statWalls) statWalls.textContent = analytics.totalWalls;
    if (statReviews) statReviews.textContent = analytics.totalReviews;
    if (statPending) statPending.textContent = analytics.pendingReviews;
    if (statRating) statRating.textContent = `${analytics.avgRating} ⭐`;
}

// Load & Render Walls
function loadWalls(searchQuery = '') {
    try {
        let walls = window.TrustWallStorage ? window.TrustWallStorage.getUserWalls() : [];
        const container = document.getElementById('wallsList');
        if (!container) return;

        if (searchQuery.trim()) {
            const q = searchQuery.trim().toLowerCase();
            walls = walls.filter(w => 
                w.title.toLowerCase().includes(q) || 
                (w.description && w.description.toLowerCase().includes(q)) ||
                w.slug.toLowerCase().includes(q)
            );
        }

        if (walls.length === 0) {
            container.innerHTML = `
                <div class="dashboard-empty-state" style="grid-column: 1/-1;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🧱</div>
                    <h3 style="margin-bottom: 0.5rem; font-size: 1.35rem;">لا توجد جدران مطابقة</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">أنشئ جدارك الأول أو جرّب البحث بكلمات أخرى</p>
                    <button onclick="openCreateModal()" class="btn-apple btn-apple-primary">+ إنشاء جدار جديد</button>
                </div>
            `;
            return;
        }

        container.innerHTML = walls.map(wall => {
            const testimonials = window.TrustWallStorage.getAllWallTestimonials(wall.id);
            const pendingCount = testimonials.filter(t => t.status === 'pending').length;
            const approvedCount = testimonials.filter(t => t.status === 'approved').length;

            return `
                <div class="wall-card" style="--card-accent: ${wall.color || 'var(--apple-blue)'};">
                    <div>
                        <div class="wall-card-header">
                            <div>
                                <h3>${escapeHtml(wall.title)}</h3>
                                <div style="display: flex; gap: 0.5rem; align-items: center; margin-top: 0.35rem;">
                                    <span class="wall-slug-tag" onclick="copyWallLink('${escapeHtml(wall.slug)}')" title="انقر لنسخ الرابط">
                                        🔗 ${escapeHtml(wall.slug)}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <p class="wall-card-desc">${escapeHtml(wall.description || 'لا يوجد وصف مخصص لهذا الجدار')}</p>
                    </div>

                    <div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">
                            <span>معتمد: <strong>${approvedCount}</strong></span>
                            <span>قيد المراجعة: <strong style="color: ${pendingCount > 0 ? 'var(--apple-gold)' : 'inherit'};">${pendingCount}</strong></span>
                            <span>📅 ${new Date(wall.created_at || Date.now()).toLocaleDateString('ar-SA')}</span>
                        </div>

                        <div class="wall-card-actions">
                            <a href="wall.html?slug=${encodeURIComponent(wall.slug)}" target="_blank" class="btn-wall-action btn-wall-view" title="عرض صفحة الجدار">
                                👁️ عرض
                            </a>
                            <a href="submit.html?slug=${encodeURIComponent(wall.slug)}" target="_blank" class="btn-wall-action btn-wall-submit" title="رابط جمع الشهادات للعملاء">
                                ✍️ رابط الجمع
                            </a>
                            <a href="embed.html?slug=${encodeURIComponent(wall.slug)}" class="btn-wall-action btn-wall-embed" title="توليد كود التضمين">
                                📎 تضمين
                            </a>
                            <button onclick="openTestimonialsModal(${wall.id})" class="btn-wall-action btn-wall-manage" title="إدارة ومراجعة الشهادات">
                                ⚙️ الشهادات (${testimonials.length})
                            </button>
                            <button onclick="deleteWall(${wall.id})" class="btn-wall-action btn-wall-delete" title="حذف الجدار">
                                🗑️
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Error loading walls:', err);
    }
}

// Search Walls Live
function setupSearch() {
    const searchInput = document.getElementById('searchWallInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        loadWalls(e.target.value);
    });
}

// Create Wall Form Setup
function setupCreateForm() {
    const form = document.getElementById('createWallForm');
    if (!form) return;

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const title = document.getElementById('wallTitle').value.trim();
        const slug = document.getElementById('wallSlug').value.trim();
        const description = document.getElementById('wallDesc').value.trim();
        const color = document.getElementById('wallColor').value;
        const welcome_message = document.getElementById('wallWelcome').value.trim();

        if (!title) return;

        try {
            if (window.TrustWallStorage) {
                const newWall = window.TrustWallStorage.createWall({
                    title,
                    slug,
                    description,
                    color,
                    welcome_message
                });

                closeCreateModal();
                form.reset();
                renderAnalytics();
                loadWalls();

                if (window.TrustWallToast) {
                    window.TrustWallToast.show(`تم إنشاء الجدار "${newWall.title}" بنجاح! 🎉`, 'success');
                }
            }
        } catch (err) {
            alert(err.message || 'حدث خطأ أثناء إنشاء الجدار');
        }
    });
}

function openCreateModal() {
    const modal = document.getElementById('createModal');
    if (modal) modal.classList.add('open');
}

function closeCreateModal() {
    const modal = document.getElementById('createModal');
    if (modal) modal.classList.remove('open');
}

function deleteWall(id) {
    if (!confirm('هل أنت متأكد من حذف هذا الجدار نهائياً؟ سيتم حذف جميع الشهادات المرتبطة به.')) return;

    try {
        if (window.TrustWallStorage) {
            window.TrustWallStorage.deleteWall(id);
            renderAnalytics();
            loadWalls();
            if (window.TrustWallToast) {
                window.TrustWallToast.show('تم حذف الجدار بنجاح', 'info');
            }
        }
    } catch (err) {
        alert('حدث خطأ أثناء الحذف');
    }
}

function copyWallLink(slug) {
    const baseUrl = window.location.href.substring(0, window.location.href.lastIndexOf('/'));
    const url = `${baseUrl}/wall.html?slug=${encodeURIComponent(slug)}`;

    navigator.clipboard.writeText(url).then(() => {
        if (window.TrustWallToast) {
            window.TrustWallToast.show('تم نسخ رابط الجدار إلى الحافظة! 📋', 'copy');
        }
    }).catch(() => {
        prompt('انسخ الرابط التالي:', url);
    });
}

// Testimonials Moderation Modal
function openTestimonialsModal(wallId) {
    currentWallId = wallId;
    currentFilterStatus = 'all';
    const modal = document.getElementById('testimonialsModal');
    if (modal) modal.classList.add('open');
    loadTestimonials();
}

function closeTestimonialsModal() {
    const modal = document.getElementById('testimonialsModal');
    if (modal) modal.classList.remove('open');
}

function setTestimonialFilter(status, btn) {
    currentFilterStatus = status;
    const filterBtns = document.querySelectorAll('.t-filter-pill');
    filterBtns.forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    loadTestimonials();
}

function loadTestimonials() {
    try {
        const wall = window.TrustWallStorage.getWallById(currentWallId);
        let testimonials = window.TrustWallStorage.getAllWallTestimonials(currentWallId);

        const modalTitle = document.getElementById('tModalTitle');
        if (modalTitle && wall) {
            modalTitle.textContent = `شهادات: ${wall.title}`;
        }

        if (currentFilterStatus !== 'all') {
            testimonials = testimonials.filter(t => t.status === currentFilterStatus);
        }

        const container = document.getElementById('testimonialsList');
        if (!container) return;

        if (testimonials.length === 0) {
            container.innerHTML = `
                <div style="text-align:center; color: var(--text-secondary); padding: 3rem 1rem;">
                    <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💌</div>
                    <p>لا توجد شهادات في هذا القسم حالياً</p>
                </div>
            `;
            return;
        }

        container.innerHTML = testimonials.map(t => {
            const statusArabic = t.status === 'approved' ? 'معتمد ✓' : t.status === 'rejected' ? 'مرفوض ✕' : 'قيد المراجعة ⏳';
            const avatarHtml = t.author_image 
                ? `<img src="${t.author_image}" class="tw-avatar-img" alt="${escapeHtml(t.author_name)}">`
                : `<div class="tw-avatar-init">${escapeHtml(t.author_name.charAt(0) || '👤')}</div>`;

            return `
                <div class="admin-testimonial-card">
                    <div class="admin-t-content">
                        <div style="display:flex; align-items:center; gap: 0.75rem; margin-bottom: 0.75rem;">
                            ${avatarHtml}
                            <div>
                                <strong style="color: var(--text-primary); font-size: 0.95rem;">${escapeHtml(t.author_name)}</strong>
                                <div style="font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(t.author_role || t.author_email || 'عميل موثق')}</div>
                            </div>
                        </div>

                        <div style="color: var(--apple-gold); margin-bottom: 0.5rem;">${'⭐'.repeat(t.rating || 5)}</div>
                        <p class="admin-t-text">"${escapeHtml(t.content)}"</p>

                        <div class="admin-t-meta">
                            <span class="status-badge status-${t.status}">${statusArabic}</span>
                            <span>📅 ${new Date(t.created_at || Date.now()).toLocaleDateString('ar-SA')}</span>
                        </div>
                    </div>

                    <div class="admin-t-actions">
                        ${t.status !== 'approved' ? `
                            <button onclick="updateTestimonialStatus(${t.id}, 'approved')" class="btn-action-icon btn-action-approve" title="قبول الشهادة">
                                ✓
                            </button>
                        ` : ''}
                        ${t.status !== 'rejected' ? `
                            <button onclick="updateTestimonialStatus(${t.id}, 'rejected')" class="btn-action-icon btn-action-reject" title="رفض الشهادة">
                                ✕
                            </button>
                        ` : ''}
                        <button onclick="deleteTestimonialItem(${t.id})" class="btn-action-icon btn-action-delete" title="حذف نهائي">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Error loading testimonials:', err);
    }
}

function updateTestimonialStatus(id, status) {
    try {
        if (window.TrustWallStorage) {
            window.TrustWallStorage.updateTestimonialStatus(id, status);
            loadTestimonials();
            renderAnalytics();
            loadWalls();

            const msg = status === 'approved' ? 'تم اعتماد الشهادة بنجاح! ستظهر على الجدار والودجت ✨' : 'تم تغيير حالة الشهادة إلى مرفوض';
            if (window.TrustWallToast) {
                window.TrustWallToast.show(msg, status === 'approved' ? 'success' : 'info');
            }
        }
    } catch (err) {
        alert('حدث خطأ');
    }
}

function deleteTestimonialItem(id) {
    if (!confirm('حذف هذه الشهادة نهائياً؟')) return;
    try {
        if (window.TrustWallStorage) {
            window.TrustWallStorage.deleteTestimonial(id);
            loadTestimonials();
            renderAnalytics();
            loadWalls();
            if (window.TrustWallToast) {
                window.TrustWallToast.show('تم حذف الشهادة', 'info');
            }
        }
    } catch (err) {
        alert('حدث خطأ');
    }
}

// Backup & Testing Utilities
function setupBackupTools() {
    const exportBtn = document.getElementById('exportDataBtn');
    const resetBtn = document.getElementById('resetDataBtn');

    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const dataStr = window.TrustWallStorage.exportData();
            const blob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `trustwall-backup-${new Date().toISOString().slice(0,10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
            if (window.TrustWallToast) {
                window.TrustWallToast.show('تم تصدير نسخة احتياطية من البيانات بنجاح 💾', 'success');
            }
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (confirm('هل تريد إعادة تعيين البيانات التجريبية إلى الإعدادات الافتراضية؟')) {
                window.TrustWallStorage.resetToDefaults();
                renderAnalytics();
                loadWalls();
                if (window.TrustWallToast) {
                    window.TrustWallToast.show('تمت استعادة البيانات التجريبية بنجاح 🔄', 'success');
                }
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
