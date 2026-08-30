/**
 * TrustWall Storage Engine (Client-side Data Persistence for GitHub Pages)
 */
(function(window) {
    const STORAGE_KEY_USERS = 'trustwall_users';
    const STORAGE_KEY_WALLS = 'trustwall_walls';
    const STORAGE_KEY_TESTIMONIALS = 'trustwall_testimonials';
    const STORAGE_KEY_CURRENT_USER = 'user';
    const STORAGE_KEY_TOKEN = 'token';

    // Helper: generate random slug
    function generateSlug() {
        return Math.random().toString(36).substring(2, 10);
    }

    // Initialize Default Seed Data
    function initSeedData() {
        if (!localStorage.getItem(STORAGE_KEY_USERS)) {
            const defaultUsers = [
                { id: 1, name: 'محمد الزروالي', email: 'demo@trustwall.com', password: 'password123' }
            ];
            localStorage.setItem(STORAGE_KEY_USERS, JSON.stringify(defaultUsers));
        }

        if (!localStorage.getItem(STORAGE_KEY_WALLS)) {
            const defaultWalls = [
                {
                    id: 1,
                    user_id: 1,
                    slug: 'demo-store',
                    title: 'متجر النخبة',
                    description: 'آراء وتقييمات عملاء متجر النخبة للمنتجات الفاخرة',
                    color: '#3b82f6',
                    welcome_message: 'شكراً لك على مشاركة تجربتك مع متجر النخبة!',
                    created_at: new Date().toISOString()
                }
            ];
            localStorage.setItem(STORAGE_KEY_WALLS, JSON.stringify(defaultWalls));
        }

        if (!localStorage.getItem(STORAGE_KEY_TESTIMONIALS)) {
            const defaultTestimonials = [
                {
                    id: 1,
                    wall_id: 1,
                    author_name: 'أحمد الفاسي',
                    author_email: 'ahmed@example.com',
                    author_image: '',
                    content: 'خدمة ممتازة وسريعة جداً، المنتج وصل في أقل من 24 ساعة وبجودة تفوق التوقعات!',
                    rating: 5,
                    status: 'approved',
                    created_at: new Date(Date.now() - 86400000 * 2).toISOString()
                },
                {
                    id: 2,
                    wall_id: 1,
                    author_name: 'سارة بنعلي',
                    author_email: 'sara@example.com',
                    author_image: '',
                    content: 'احترافية عالية جداً والتعامل راقي وسلس. منصة سهلت علينا الكثير وأنصح بها بشدة.',
                    rating: 5,
                    status: 'approved',
                    created_at: new Date(Date.now() - 86400000).toISOString()
                },
                {
                    id: 3,
                    wall_id: 1,
                    author_name: 'كريم المنصوري',
                    author_email: 'karim@example.com',
                    author_image: '',
                    content: 'تجربة رائعة وتصميم أنيق جداً. زادت مبيعاتنا وثقة العملاء بفضل إظهار الشهادات.',
                    rating: 5,
                    status: 'pending',
                    created_at: new Date().toISOString()
                }
            ];
            localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(defaultTestimonials));
        }
    }

    initSeedData();

    const TrustWallStorage = {
        // --- Auth ---
        register(name, email, password) {
            const users = JSON.parse(localStorage.getItem(STORAGE_KEY_USERS) || '[]');
            if (users.some(u => u.email.toLowerCase() === email.toLowerCase())) {
                throw new Error('البريد الإلكتروني مستخدم بالفعل');
            }
            const newUser = {
                id: Date.now(),
                name,
                email,
                password
            };
            users.push(newUser);
            localStorage.setItem(STORAGE_KEY_USERS, JSON.stringify(users));

            const token = 'token_' + Math.random().toString(36).substring(2);
            this.setSession(newUser, token);
            return { user: newUser, token };
        },

        login(email, password) {
            const users = JSON.parse(localStorage.getItem(STORAGE_KEY_USERS) || '[]');
            const user = users.find(u => u.email.toLowerCase() === email.toLowerCase() && u.password === password);
            if (!user) {
                throw new Error('بيانات الدخول غير صحيحة');
            }
            const token = 'token_' + Math.random().toString(36).substring(2);
            this.setSession(user, token);
            return { user, token };
        },

        setSession(user, token) {
            localStorage.setItem(STORAGE_KEY_CURRENT_USER, JSON.stringify({ id: user.id, name: user.name, email: user.email }));
            localStorage.setItem(STORAGE_KEY_TOKEN, token);
        },

        getCurrentUser() {
            try {
                return JSON.parse(localStorage.getItem(STORAGE_KEY_CURRENT_USER) || 'null');
            } catch (e) {
                return null;
            }
        },

        getToken() {
            return localStorage.getItem(STORAGE_KEY_TOKEN);
        },

        logout() {
            localStorage.removeItem(STORAGE_KEY_CURRENT_USER);
            localStorage.removeItem(STORAGE_KEY_TOKEN);
        },

        // --- Walls ---
        getUserWalls() {
            const user = this.getCurrentUser();
            const walls = JSON.parse(localStorage.getItem(STORAGE_KEY_WALLS) || '[]');
            if (!user) return walls;
            // Return walls created by current user, or all walls if demo
            const userWalls = walls.filter(w => w.user_id === user.id);
            return userWalls.length > 0 ? userWalls : walls;
        },

        getWallBySlug(slug) {
            if (!slug) return null;
            const walls = JSON.parse(localStorage.getItem(STORAGE_KEY_WALLS) || '[]');
            return walls.find(w => w.slug === slug || w.slug.toLowerCase() === slug.toLowerCase()) || null;
        },

        createWall({ title, description, color, welcome_message }) {
            const user = this.getCurrentUser() || { id: 1 };
            const walls = JSON.parse(localStorage.getItem(STORAGE_KEY_WALLS) || '[]');
            const newWall = {
                id: Date.now(),
                user_id: user.id,
                slug: generateSlug(),
                title,
                description: description || '',
                color: color || '#3b82f6',
                welcome_message: welcome_message || 'شكراً لك على مشاركة تجربتك معنا!',
                created_at: new Date().toISOString()
            };
            walls.unshift(newWall);
            localStorage.setItem(STORAGE_KEY_WALLS, JSON.stringify(walls));
            return newWall;
        },

        deleteWall(id) {
            let walls = JSON.parse(localStorage.getItem(STORAGE_KEY_WALLS) || '[]');
            walls = walls.filter(w => w.id !== Number(id));
            localStorage.setItem(STORAGE_KEY_WALLS, JSON.stringify(walls));

            // Also remove testimonials for this wall
            let testimonials = JSON.parse(localStorage.getItem(STORAGE_KEY_TESTIMONIALS) || '[]');
            testimonials = testimonials.filter(t => t.wall_id !== Number(id));
            localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(testimonials));
        },

        // --- Testimonials ---
        getWallTestimonials(wallId, filterStatus = null) {
            const testimonials = JSON.parse(localStorage.getItem(STORAGE_KEY_TESTIMONIALS) || '[]');
            return testimonials.filter(t => {
                const matchWall = t.wall_id === Number(wallId);
                if (!filterStatus) return matchWall;
                return matchWall && t.status === filterStatus;
            });
        },

        getAllWallTestimonials(wallId) {
            const testimonials = JSON.parse(localStorage.getItem(STORAGE_KEY_TESTIMONIALS) || '[]');
            return testimonials.filter(t => t.wall_id === Number(wallId));
        },

        addTestimonial(slug, { author_name, author_email, author_image, content, rating }) {
            const wall = this.getWallBySlug(slug);
            if (!wall) throw new Error('الجدار غير موجود');

            const testimonials = JSON.parse(localStorage.getItem(STORAGE_KEY_TESTIMONIALS) || '[]');
            const newTestimonial = {
                id: Date.now(),
                wall_id: wall.id,
                author_name,
                author_email: author_email || '',
                author_image: author_image || '',
                content,
                rating: Number(rating) || 5,
                status: 'pending',
                created_at: new Date().toISOString()
            };
            testimonials.unshift(newTestimonial);
            localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(testimonials));
            return newTestimonial;
        },

        updateTestimonialStatus(id, status) {
            const testimonials = JSON.parse(localStorage.getItem(STORAGE_KEY_TESTIMONIALS) || '[]');
            const target = testimonials.find(t => t.id === Number(id));
            if (target) {
                target.status = status;
                localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(testimonials));
            }
            return target;
        },

        deleteTestimonial(id) {
            let testimonials = JSON.parse(localStorage.getItem(STORAGE_KEY_TESTIMONIALS) || '[]');
            testimonials = testimonials.filter(t => t.id !== Number(id));
            localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(testimonials));
        },

        // --- Helpers ---
        getSlugFromUrl() {
            const urlParams = new URLSearchParams(window.location.search);
            const slugFromParam = urlParams.get('slug');
            if (slugFromParam) return slugFromParam;

            // Check hash #slug
            if (window.location.hash && window.location.hash.length > 1) {
                return window.location.hash.substring(1);
            }

            // Path fallback: /wall/demo-store or /wall.html
            const parts = window.location.pathname.split('/').filter(Boolean);
            const lastPart = parts[parts.length - 1] || '';
            if (lastPart && !lastPart.endsWith('.html') && lastPart !== 'wall' && lastPart !== 'submit' && lastPart !== 'embed') {
                return lastPart;
            }
            return 'demo-store'; // Default fallback
        },

        fileToBase64(file) {
            return new Promise((resolve, reject) => {
                if (!file) {
                    resolve('');
                    return;
                }
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result);
                reader.onerror = error => reject(error);
            });
        }
    };

    window.TrustWallStorage = TrustWallStorage;
})(window);
