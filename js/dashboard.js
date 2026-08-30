// Dashboard Logic for TrustWall
let currentWallId = null;

// Auth check
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || 'null');

if (!token && !user) {
    window.location.href = 'login.html';
}

// Show user name
document.addEventListener('DOMContentLoaded', () => {
    const userNameEl = document.getElementById('userName');
    if (userNameEl && user && user.name) {
        userNameEl.textContent = 'مرحباً، ' + user.name;
    }

    loadWalls();
    setupCreateForm();
});

// Load and Render Walls
function loadWalls() {
    try {
        const walls = window.TrustWallStorage ? window.TrustWallStorage.getUserWalls() : [];
        const container = document.getElementById('wallsList');
        if (!container) return;

        if (walls.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <h3>لا يوجد جدران بعد</h3>
                    <p>أنشئ أول جدار لجمع شهادات عملائك</p>
                </div>
            `;
            return;
        }

        container.innerHTML = walls.map(wall => `
            <div class="wall-card" style="border-right-color: ${wall.color || 'var(--primary)'}">
                <div class="wall-card-header">
                    <div>
                        <h3>${escapeHtml(wall.title)}</h3>
                        <div class="wall-card-meta">
                            <span>📅 ${new Date(wall.created_at || Date.now()).toLocaleDateString('ar-SA')}</span>
                        </div>
                    </div>
                </div>
                <p style="color: var(--gray); margin-bottom: 1rem;">${escapeHtml(wall.description || 'لا يوجد وصف')}</p>
                <div class="wall-card-actions">
                    <a href="wall.html?slug=${encodeURIComponent(wall.slug)}" target="_blank" class="btn-view">👁️ عرض</a>
                    <a href="submit.html?slug=${encodeURIComponent(wall.slug)}" target="_blank" class="btn-submit">✍️ رابط الجمع</a>
                    <a href="embed.html?slug=${encodeURIComponent(wall.slug)}" class="btn-embed">📎 تضمين</a>
                    <button onclick="openTestimonialsModal(${wall.id})" class="btn-manage">⚙️ إدارة</button>
                    <button onclick="deleteWall(${wall.id})" class="btn-delete">🗑️ حذف</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Error loading walls:', err);
    }
}

// Setup Create Wall Form
function setupCreateForm() {
    const createForm = document.getElementById('createWallForm');
    if (!createForm) return;

    createForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const title = document.getElementById('wallTitle').value.trim();
        const description = document.getElementById('wallDesc').value.trim();
        const color = document.getElementById('wallColor').value;
        const welcome_message = document.getElementById('wallWelcome').value.trim();

        if (!title) return;

        try {
            if (window.TrustWallStorage) {
                window.TrustWallStorage.createWall({
                    title,
                    description,
                    color,
                    welcome_message
                });
            }
            closeCreateModal();
            createForm.reset();
            loadWalls();
        } catch (err) {
            alert('حدث خطأ أثناء إنشاء الجدار');
        }
    });
}

// Modal Controls
function openCreateModal() {
    const modal = document.getElementById('createModal');
    if (modal) modal.style.display = 'flex';
}

function closeCreateModal() {
    const modal = document.getElementById('createModal');
    if (modal) modal.style.display = 'none';
}

// Delete Wall
function deleteWall(id) {
    if (!confirm('هل أنت متأكد من حذف هذا الجدار؟ سيتم حذف جميع الشهادات التابعة له أيضاً.')) return;

    try {
        if (window.TrustWallStorage) {
            window.TrustWallStorage.deleteWall(id);
            loadWalls();
        }
    } catch (err) {
        alert('حدث خطأ أثناء الحذف');
    }
}

// Testimonials Modal Management
function openTestimonialsModal(wallId) {
    currentWallId = wallId;
    const modal = document.getElementById('testimonialsModal');
    if (modal) modal.style.display = 'flex';
    loadTestimonials(wallId);
}

function closeTestimonialsModal() {
    const modal = document.getElementById('testimonialsModal');
    if (modal) modal.style.display = 'none';
}

function loadTestimonials(wallId) {
    try {
        const testimonials = window.TrustWallStorage ? window.TrustWallStorage.getAllWallTestimonials(wallId) : [];
        const container = document.getElementById('testimonialsList');
        if (!container) return;

        if (testimonials.length === 0) {
            container.innerHTML = '<p style="text-align:center; color: var(--gray); padding: 2rem 0;">لا توجد شهادات بعد</p>';
            return;
        }

        container.innerHTML = testimonials.map(t => {
            const statusArabic = t.status === 'approved' ? 'معتمد' : t.status === 'rejected' ? 'مرفوض' : 'قيد المراجعة';
            return `
                <div class="testimonial-item">
                    <div class="testimonial-item-content">
                        <p style="font-size: 1.05rem; margin-bottom: 0.5rem;">${escapeHtml(t.content)}</p>
                        <div class="testimonial-item-meta">
                            <span>👤 ${escapeHtml(t.author_name)}</span>
                            <span>⭐ ${t.rating}/5</span>
                            <span class="status-badge status-${t.status}">${statusArabic}</span>
                            <span>📅 ${new Date(t.created_at || Date.now()).toLocaleDateString('ar-SA')}</span>
                        </div>
                    </div>
                    <div class="testimonial-actions">
                        ${t.status !== 'approved' ? `<button onclick="updateStatus(${t.id}, 'approved')" class="btn-approve">✓ قبول</button>` : ''}
                        ${t.status !== 'rejected' ? `<button onclick="updateStatus(${t.id}, 'rejected')" class="btn-reject">✕ رفض</button>` : ''}
                        <button onclick="deleteTestimonial(${t.id})" class="btn-delete" title="حذف">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Error loading testimonials:', err);
    }
}

function updateStatus(id, status) {
    try {
        if (window.TrustWallStorage) {
            window.TrustWallStorage.updateTestimonialStatus(id, status);
            loadTestimonials(currentWallId);
        }
    } catch (err) {
        alert('حدث خطأ أثناء تعديل الحالة');
    }
}

function deleteTestimonial(id) {
    if (!confirm('هل أنت متأكد من حذف هذه الشهادة؟')) return;
    try {
        if (window.TrustWallStorage) {
            window.TrustWallStorage.deleteTestimonial(id);
            loadTestimonials(currentWallId);
        }
    } catch (err) {
        alert('حدث خطأ أثناء حذف الشهادة');
    }
}

// Utility: HTML escaping to prevent XSS
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
