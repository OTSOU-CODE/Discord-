/**
 * TrustWall Landing Page — GSAP Animations & Interactive Controller
 */
document.addEventListener('DOMContentLoaded', () => {
    initAuthNavState();
    initGsapHeroAnimations();
    initCounterAnimations();
    initPlaygroundController();
    initPricingSwitcher();
});

// Update navigation depending on user session
function initAuthNavState() {
    const user = window.TrustWallStorage ? window.TrustWallStorage.getCurrentUser() : null;
    const navLinksContainer = document.getElementById('appleNavLinks');
    if (navLinksContainer && user) {
        navLinksContainer.innerHTML = `
            <a href="dashboard.html" class="btn-apple btn-apple-primary">لوحة التحكم 🚀</a>
            <button onclick="logout()" class="btn-apple btn-apple-secondary">خروج</button>
        `;
    }
}

// GSAP Fluid Animations
function initGsapHeroAnimations() {
    if (typeof gsap === 'undefined') return;

    // Timeline for Hero Entrance
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.from('.hero-pill', { opacity: 0, y: 20, duration: 0.8, delay: 0.1 })
      .from('.hero-title', { opacity: 0, y: 30, duration: 0.9 }, '-=0.5')
      .from('.hero-subtitle', { opacity: 0, y: 20, duration: 0.8 }, '-=0.6')
      .from('.hero-actions', { opacity: 0, y: 20, duration: 0.8 }, '-=0.6')
      .from('.hero-float-card', { opacity: 0, y: 40, stagger: 0.15, duration: 1 }, '-=0.5');

    // Floating 3D Hover Physics
    gsap.to('.hero-float-card:nth-child(1)', {
        y: '-=12',
        duration: 3,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut'
    });

    gsap.to('.hero-float-card:nth-child(2)', {
        y: '-=18',
        duration: 3.6,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        delay: 0.5
    });

    gsap.to('.hero-float-card:nth-child(3)', {
        y: '-=10',
        duration: 2.8,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        delay: 1
    });
}

// Numeric Stats Counter Animation
function initCounterAnimations() {
    const statElements = document.querySelectorAll('.counter-anim');
    if (!statElements.length) return;

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const targetVal = parseInt(el.getAttribute('data-target') || '0', 10);
                const prefix = el.getAttribute('data-prefix') || '';
                const suffix = el.getAttribute('data-suffix') || '';

                if (typeof gsap !== 'undefined') {
                    const counterObj = { val: 0 };
                    gsap.to(counterObj, {
                        val: targetVal,
                        duration: 2,
                        ease: 'power2.out',
                        onUpdate: () => {
                            el.textContent = `${prefix}${Math.floor(counterObj.val).toLocaleString('ar-EG')}${suffix}`;
                        }
                    });
                } else {
                    el.textContent = `${prefix}${targetVal}${suffix}`;
                }
                obs.unobserve(el);
            }
        });
    }, { threshold: 0.4 });

    statElements.forEach(el => observer.observe(el));
}

// Interactive Live Widget Playground on Landing Page
function initPlaygroundController() {
    const pills = document.querySelectorAll('.theme-pill');
    const canvas = document.getElementById('playgroundCanvas');
    if (!pills.length || !canvas) return;

    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            pills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const theme = pill.getAttribute('data-theme');
            applyPlaygroundTheme(theme, canvas);

            if (window.TrustWallToast) {
                window.TrustWallToast.show(`تم تطبيق نمط: ${pill.textContent.trim()}`, 'info', 1800);
            }
        });
    });
}

function applyPlaygroundTheme(theme, canvas) {
    const cards = canvas.querySelectorAll('.tw-card');

    if (theme === 'dark') {
        canvas.style.background = '#0a0a0c';
        cards.forEach(c => {
            c.style.background = '#18181b';
            c.style.color = '#ffffff';
            c.style.borderColor = 'rgba(255, 255, 255, 0.12)';
            const text = c.querySelector('.tw-card-text');
            if (text) text.style.color = '#e4e4e7';
            const name = c.querySelector('.tw-author-name');
            if (name) name.style.color = '#ffffff';
        });
    } else if (theme === 'glass') {
        canvas.style.background = 'linear-gradient(135deg, #e0e7ff 0%, #f1f5f9 100%)';
        cards.forEach(c => {
            c.style.background = 'rgba(255, 255, 255, 0.65)';
            c.style.backdropFilter = 'blur(16px)';
            c.style.borderColor = 'rgba(255, 255, 255, 0.8)';
            c.style.color = '#1d1d1f';
            const text = c.querySelector('.tw-card-text');
            if (text) text.style.color = '#1d1d1f';
            const name = c.querySelector('.tw-author-name');
            if (name) name.style.color = '#000000';
        });
    } else if (theme === 'gold') {
        canvas.style.background = '#1c1917';
        cards.forEach(c => {
            c.style.background = '#292524';
            c.style.borderColor = '#d97706';
            c.style.borderTop = '3px solid #f59e0b';
            c.style.color = '#fef3c7';
            const text = c.querySelector('.tw-card-text');
            if (text) text.style.color = '#fde68a';
            const name = c.querySelector('.tw-author-name');
            if (name) name.style.color = '#ffffff';
        });
    } else {
        // Apple Light default
        canvas.style.background = '#f8fafc';
        cards.forEach(c => {
            c.style.background = '#ffffff';
            c.style.color = '#1d1d1f';
            c.style.borderColor = 'rgba(0, 0, 0, 0.06)';
            c.style.borderTop = '3px solid var(--apple-blue)';
            const text = c.querySelector('.tw-card-text');
            if (text) text.style.color = '#1d1d1f';
            const name = c.querySelector('.tw-author-name');
            if (name) name.style.color = '#1d1d1f';
        });
    }
}

// Pricing Toggle (Monthly vs Annual)
function initPricingSwitcher() {
    const toggle = document.getElementById('billingToggle');
    const proPriceEl = document.getElementById('proPriceVal');
    if (!toggle || !proPriceEl) return;

    toggle.addEventListener('change', () => {
        if (toggle.checked) {
            proPriceEl.innerHTML = '7$<span>/شهرياً (تدفع سنوياً)</span>';
            if (window.TrustWallToast) {
                window.TrustWallToast.show('تم تفعيل خصم الدفع السنوي (وفر 25%) 🎉', 'success', 2500);
            }
        } else {
            proPriceEl.innerHTML = '9$<span>/شهر</span>';
        }
    });
}
