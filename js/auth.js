// Auth handling for TrustWall
document.addEventListener('DOMContentLoaded', () => {
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

            try {
                if (window.TrustWallStorage) {
                    window.TrustWallStorage.register(name, email, password);
                    window.location.href = 'dashboard.html';
                } else {
                    const res = await fetch('/api/auth/register', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, email, password })
                    });
                    const data = await res.json();
                    if (!res.ok) {
                        if (errorMsg) {
                            errorMsg.textContent = data.error || 'حدث خطأ في التسجيل';
                            errorMsg.style.display = 'block';
                        }
                        return;
                    }
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    window.location.href = 'dashboard.html';
                }
            } catch (err) {
                if (errorMsg) {
                    errorMsg.textContent = err.message || 'حدث خطأ أثناء التسجيل';
                    errorMsg.style.display = 'block';
                }
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
                    window.location.href = 'dashboard.html';
                } else {
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, password })
                    });
                    const data = await res.json();
                    if (!res.ok) {
                        if (errorMsg) {
                            errorMsg.textContent = data.error || 'بيانات الدخول غير صحيحة';
                            errorMsg.style.display = 'block';
                        }
                        return;
                    }
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    window.location.href = 'dashboard.html';
                }
            } catch (err) {
                if (errorMsg) {
                    errorMsg.textContent = err.message || 'بيانات الدخول غير صحيحة';
                    errorMsg.style.display = 'block';
                }
            }
        });
    }
});

// Global Logout function
function logout() {
    if (window.TrustWallStorage) {
        window.TrustWallStorage.logout();
    } else {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }
    window.location.href = 'index.html';
}
