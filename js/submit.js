// Submit Testimonial Logic for TrustWall
document.addEventListener('DOMContentLoaded', () => {
    const slug = window.TrustWallStorage ? window.TrustWallStorage.getSlugFromUrl() : 'demo-store';
    loadWallInfo(slug);
    setupSubmitForm(slug);
});

function loadWallInfo(slug) {
    try {
        const wall = window.TrustWallStorage ? window.TrustWallStorage.getWallBySlug(slug) : null;
        if (wall && wall.welcome_message) {
            const welcomeEl = document.getElementById('welcomeMsg');
            if (welcomeEl) welcomeEl.textContent = wall.welcome_message;
        }
    } catch (err) {
        console.error('Error loading wall info:', err);
    }
}

function setupSubmitForm(slug) {
    const form = document.getElementById('submitForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        const errorMsg = document.getElementById('errorMsg');
        const successMsg = document.getElementById('successMsg');
        if (errorMsg) errorMsg.style.display = 'none';

        const author_name = form.elements['author_name'].value.trim();
        const author_email = form.elements['author_email'].value.trim();
        const rating = form.elements['rating'].value;
        const content = form.elements['content'].value.trim();
        const imageFile = form.elements['image'] ? form.elements['image'].files[0] : null;

        try {
            let author_image = '';
            if (imageFile && window.TrustWallStorage) {
                author_image = await window.TrustWallStorage.fileToBase64(imageFile);
            }

            if (window.TrustWallStorage) {
                window.TrustWallStorage.addTestimonial(slug, {
                    author_name,
                    author_email,
                    author_image,
                    content,
                    rating
                });

                form.style.display = 'none';
                if (successMsg) successMsg.style.display = 'block';
            } else {
                const formData = new FormData(form);
                const res = await fetch(`/api/walls/${slug}/testimonials`, {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (res.ok) {
                    form.style.display = 'none';
                    if (successMsg) successMsg.style.display = 'block';
                } else {
                    if (errorMsg) {
                        errorMsg.textContent = data.error || 'حدث خطأ أثناء الإرسال';
                        errorMsg.style.display = 'block';
                    }
                    if (submitBtn) submitBtn.disabled = false;
                }
            }
        } catch (err) {
            if (errorMsg) {
                errorMsg.textContent = err.message || 'حدث خطأ أثناء إرسال الشهادة';
                errorMsg.style.display = 'block';
            }
            if (submitBtn) submitBtn.disabled = false;
        }
    });
}
