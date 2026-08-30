/**
 * TrustWall Authentication Logic & One-Click Demo Mode
 */
document.addEventListener('DOMContentLoaded', () => {
    // Quick Demo Mode Button
    const demoBtn = document.getElementById('quickDemoBtn');
    if (demoBtn) {
        demoBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (window.TrustWallStorage) {
                window.TrustWallStorage.demoLogin();
                if (window.TrustWallToast) {
                    window.TrustWallToast.show('مرحباً بك! تم تسجيل الدخول بالحساب التجريبي 🚀', 'success', 2000);
                }
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 400);
            }
        });
    }

    // Register Form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorMsg = document.getElementById('errorMsg');
            if (errorMsg) errorMsg.style.display = 'none';

            const name = document.getElementById('name').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;

            if (!name || !email || !password) {
                showError('يرجى ملء جميع الحقول المطلوبة');
                return;
            }

            try {
                if (window.TrustWallStorage) {
                    window.TrustWallStorage.register(name, email, password);
                    if (window.TrustWallToast) {
                        window.TrustWallToast.show('تم إنشاء حسابك بنجاح! جاري التحويل...', 'success', 2000);
                    }
                    setTimeout(() => {
                        window.location.href = 'dashboard.html';
                    }, 400);
                }
            } catch (err) {
                showError(err.message || 'حدث خطأ أثناء إنشاء الحساب');
            }
        });
    }

    // Login Form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorMsg = document.getElementById('errorMsg');
            if (errorMsg) errorMsg.style.display = 'none';

            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;

            try {
                if (window.TrustWallStorage) {
                    window.TrustWallStorage.login(email, password);
                    if (window.TrustWallToast) {
                        window.TrustWallToast.show('أهلاً بعودتك! جاري الدخول...', 'success', 2000);
                    }
                    setTimeout(() => {
                        window.location.href = 'dashboard.html';
                    }, 400);
                }
            } catch (err) {
                showError(err.message || 'بيانات الدخول غير صحيحة');
            }
        });
    }
});

function showError(msg) {
    const errorMsg = document.getElementById('errorMsg');
    if (errorMsg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = 'block';
    }
    if (window.TrustWallToast) {
        window.TrustWallToast.show(msg, 'error', 3000);
    }
}

// Global Logout
function logout() {
    if (window.TrustWallStorage) {
        window.TrustWallStorage.logout();
    } else {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }
    window.location.href = 'index.html';
}
