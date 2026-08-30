// Main JS for TrustWall Landing Page
document.addEventListener('DOMContentLoaded', () => {
    // Dynamic navigation state based on auth status
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || 'null');

    const navLinks = document.querySelector('.nav-links');
    if (navLinks && (token || user)) {
        navLinks.innerHTML = `
            <a href="dashboard.html" class="btn-primary">لوحة التحكم 🚀</a>
        `;
    }
});
