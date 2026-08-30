/**
 * TrustWall — Interactive Split-View Submission Logic
 */
let currentRating = 5;
let uploadedBase64Image = '';
let targetSlug = 'elite-store';

const ratingLabels = {
    5: 'ممتاز واستثنائي! 🌟',
    4: 'تجربة رائعة جداً 👍',
    3: 'جيد ومقبول 🙂',
    2: 'أقل من المتوقع 😐',
    1: 'تجربة غير مرضية 😞'
};

document.addEventListener('DOMContentLoaded', () => {
    targetSlug = window.TrustWallStorage ? window.TrustWallStorage.getSlugFromUrl() : 'elite-store';
    loadWallDetails();
    setupLivePreview();
    setupStarRating();
    setupImageUploader();
    setupFormSubmission();
});

function loadWallDetails() {
    try {
        const wall = window.TrustWallStorage ? window.TrustWallStorage.getWallBySlug(targetSlug) : null;
        if (wall) {
            const welcomeEl = document.getElementById('welcomeMsg');
            const subTitleEl = document.getElementById('welcomeSub');
            if (welcomeEl) welcomeEl.textContent = wall.welcome_message || `شاركنا رأيك في ${wall.title}`;
            if (subTitleEl) subTitleEl.textContent = `شهادتك تهمنا في ${wall.title}`;
            document.documentElement.style.setProperty('--preview-accent', wall.color || '#0071e3');
        }
    } catch (err) {
        console.error('Error loading wall:', err);
    }
}

// Live Card Preview Sync
function setupLivePreview() {
    const nameInput = document.getElementById('authorNameInput');
    const roleInput = document.getElementById('authorRoleInput');
    const contentInput = document.getElementById('contentInput');

    const previewName = document.getElementById('previewName');
    const previewRole = document.getElementById('previewRole');
    const previewText = document.getElementById('previewText');
    const previewAvatar = document.getElementById('previewAvatar');

    if (nameInput && previewName) {
        nameInput.addEventListener('input', () => {
            const val = nameInput.value.trim() || 'اسمك الكامل';
            previewName.textContent = val;
            if (!uploadedBase64Image && previewAvatar) {
                previewAvatar.innerHTML = `<div class="preview-avatar-init">${escapeHtml(val.charAt(0) || '👤')}</div>`;
            }
        });
    }

    if (roleInput && previewRole) {
        roleInput.addEventListener('input', () => {
            previewRole.textContent = roleInput.value.trim() || 'عميل موثق';
        });
    }

    if (contentInput && previewText) {
        contentInput.addEventListener('input', () => {
            previewText.textContent = `"${contentInput.value.trim() || 'اكتب رأيك وتجربتك هنا وستظهر مباشرة في المعاينة...'}"`;
        });
    }
}

// Star Rating Interaction
function setupStarRating() {
    const starBtns = document.querySelectorAll('.star-btn');
    const emotionEl = document.getElementById('ratingEmotion');
    const hiddenRatingInput = document.getElementById('ratingInput');

    function updateStarsDisplay(rating) {
        starBtns.forEach(btn => {
            const val = parseInt(btn.getAttribute('data-val'), 10);
            if (val <= rating) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });

        if (emotionEl) {
            emotionEl.textContent = ratingLabels[rating] || '';
        }

        const previewStarsEl = document.getElementById('previewStars');
        if (previewStarsEl) {
            previewStarsEl.textContent = '⭐'.repeat(rating);
        }
    }

    starBtns.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            const val = parseInt(btn.getAttribute('data-val'), 10);
            starBtns.forEach(b => {
                const bVal = parseInt(b.getAttribute('data-val'), 10);
                if (bVal <= val) {
                    b.classList.add('hovered');
                } else {
                    b.classList.remove('hovered');
                }
            });
            if (emotionEl) emotionEl.textContent = ratingLabels[val] || '';
        });

        btn.addEventListener('mouseleave', () => {
            starBtns.forEach(b => b.classList.remove('hovered'));
            updateStarsDisplay(currentRating);
        });

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            currentRating = parseInt(btn.getAttribute('data-val'), 10);
            if (hiddenRatingInput) hiddenRatingInput.value = currentRating;
            updateStarsDisplay(currentRating);
        });
    });

    updateStarsDisplay(currentRating);
}

// Drag & Drop Image Uploader
function setupImageUploader() {
    const zone = document.getElementById('avatarDropZone');
    const fileInput = document.getElementById('avatarFileInput');
    const previewAvatar = document.getElementById('previewAvatar');

    if (!zone || !fileInput) return;

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleAvatarFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleAvatarFile(fileInput.files[0]);
        }
    });

    function handleAvatarFile(file) {
        if (!file.type.startsWith('image/')) {
            alert('يرجى اختيار ملف صورة صالح (JPEG, PNG, WebP)');
            return;
        }

        const uploadText = zone.querySelector('.upload-text');
        if (uploadText) uploadText.textContent = `تم اختيار: ${file.name}`;

        if (window.TrustWallStorage) {
            window.TrustWallStorage.fileToBase64(file).then(base64 => {
                uploadedBase64Image = base64;
                if (previewAvatar) {
                    previewAvatar.innerHTML = `<img src="${base64}" class="preview-avatar-img" alt="Avatar">`;
                }
            });
        }
    }
}

// Form Submission
function setupFormSubmission() {
    const form = document.getElementById('testimonialSubmitForm');
    if (!form) return;

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        const name = document.getElementById('authorNameInput').value.trim();
        const email = document.getElementById('authorEmailInput').value.trim();
        const role = document.getElementById('authorRoleInput').value.trim();
        const content = document.getElementById('contentInput').value.trim();

        if (!name || !content) {
            alert('يرجى إدخال اسمك ورأيك');
            if (submitBtn) submitBtn.disabled = false;
            return;
        }

        try {
            if (window.TrustWallStorage) {
                window.TrustWallStorage.addTestimonial(targetSlug, {
                    author_name: name,
                    author_email: email,
                    author_role: role || 'عميل موثق',
                    author_image: uploadedBase64Image,
                    content: content,
                    rating: currentRating
                });

                // Show Success Screen
                document.getElementById('formSection').style.display = 'none';
                const successCard = document.getElementById('successCard');
                if (successCard) successCard.style.display = 'block';

                const viewWallBtn = document.getElementById('viewWallLink');
                if (viewWallBtn) {
                    viewWallBtn.href = `wall.html?slug=${encodeURIComponent(targetSlug)}`;
                }

                if (window.TrustWallToast) {
                    window.TrustWallToast.show('تم إرسال شهادتك بنجاح! شكراً جزيلاً لك 🎉', 'success', 3500);
                }
            }
        } catch (err) {
            alert(err.message || 'حدث خطأ أثناء الإرسال');
            if (submitBtn) submitBtn.disabled = false;
        }
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[m]));
}
