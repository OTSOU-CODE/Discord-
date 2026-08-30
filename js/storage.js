/**
 * TrustWall Storage Engine (Apple-Grade Client Persistence & State Management)
 */
(function(window) {
    const STORAGE_KEY_USERS = 'trustwall_users_v2';
    const STORAGE_KEY_WALLS = 'trustwall_walls_v2';
    const STORAGE_KEY_TESTIMONIALS = 'trustwall_testimonials_v2';
    const STORAGE_KEY_CURRENT_USER = 'user';
    const STORAGE_KEY_TOKEN = 'token';

    function generateSlug(prefix = '') {
        const rand = Math.random().toString(36).substring(2, 8);
        return prefix ? `${prefix}-${rand}` : rand;
    }

    function initSeedData() {
        if (!localStorage.getItem(STORAGE_KEY_USERS)) {
            const defaultUsers = [
                { id: 1, name: 'محمد الزروالي', email: 'demo@trustwall.com', password: 'password123', plan: 'pro' }
            ];
            localStorage.setItem(STORAGE_KEY_USERS, JSON.stringify(defaultUsers));
        }

        if (!localStorage.getItem(STORAGE_KEY_WALLS)) {
            const defaultWalls = [
                {
                    id: 1,
                    user_id: 1,
                    slug: 'elite-store',
                    title: 'متجر النخبة الفاخر ✨',
                    description: 'آراء وتقييمات عملاء متجر النخبة للمنتجات الحصرية والفاخرة',
                    color: '#0071e3',
                    welcome_message: 'مرحباً بك! يسعدنا جداً سماع رأيك وتجربتك في الشراء من متجر النخبة',
                    created_at: new Date(Date.now() - 86400000 * 7).toISOString()
                },
                {
                    id: 2,
                    user_id: 1,
                    slug: 'sahab-app',
                    title: 'تطبيق سحاب — SaaS ☁️',
                    description: 'تجارب مستخدمي منصة سحاب لإدارة المشروعات والإنتاجية الرقمية',
                    color: '#6366f1',
                    welcome_message: 'كيف ساعدتك منصة سحاب في تحسين إنتاجيتك وإدارة فريقك؟ شاركنا رأيك!',
                    created_at: new Date(Date.now() - 86400000 * 4).toISOString()
                },
                {
                    id: 3,
                    user_id: 1,
                    slug: 'reyada-agency',
                    title: 'وكالة ريادة للإبداع والتصميم 🎨',
                    description: 'شهادات شركائنا وعملائنا في خدمات تصميم الهوية الرقمية وتطوير المواقع',
                    color: '#8b5cf6',
                    welcome_message: 'شكراً لاختيارك وكالة ريادة! شاركنا انطباعك عن العمل مع فريقنا الإبداعي',
                    created_at: new Date(Date.now() - 86400000 * 2).toISOString()
                }
            ];
            localStorage.setItem(STORAGE_KEY_WALLS, JSON.stringify(defaultWalls));
        }

        if (!localStorage.getItem(STORAGE_KEY_TESTIMONIALS)) {
            const defaultTestimonials = [
                {
                    id: 101,
                    wall_id: 1,
                    author_name: 'أحمد الفاسي',
                    author_email: 'ahmed@alfasi.com',
                    author_image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&auto=format&fit=crop&q=80',
                    author_role: 'رائد أعمال — كازابلانكا',
                    content: 'تجربة تسوق تفوق الوصف! المنتجات وصلت في أقل من 24 ساعة بتغليف فاخر وأنيق جداً. الجودة استثنائية وخدمة العملاء على أعلى مستوى من الاحترافية.',
                    rating: 5,
                    verified: true,
                    status: 'approved',
                    created_at: new Date(Date.now() - 86400000 * 5).toISOString()
                },
                {
                    id: 102,
                    wall_id: 1,
                    author_name: 'سارة بنعلي',
                    author_email: 'sara.benali@gmail.com',
                    author_image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=120&auto=format&fit=crop&q=80',
                    author_role: 'مديرة تسويق رقمي',
                    content: 'التجربة كانت ممتازة من البداية للنهاية. سهولة في الطلب وتحديثات مستمرة حتى وصل الطرد. أنصح بالتعامل معهم بشدة وبكل ثقة.',
                    rating: 5,
                    verified: true,
                    status: 'approved',
                    created_at: new Date(Date.now() - 86400000 * 4).toISOString()
                },
                {
                    id: 103,
                    wall_id: 1,
                    author_name: 'كريم المنصوري',
                    author_email: 'karim.m@outlook.com',
                    author_image: '',
                    author_role: 'مهندس برمجيات',
                    content: 'طلبت هدية لصديقي وطلبت تغليفاً خاصاً، والنتيجة كانت مبهرة وفاقت توقعاتي. شكراً لفريق العمل المتميز!',
                    rating: 5,
                    verified: true,
                    status: 'approved',
                    created_at: new Date(Date.now() - 86400000 * 2).toISOString()
                },
                {
                    id: 104,
                    wall_id: 1,
                    author_name: 'هدى العمراني',
                    author_email: 'houda.om@yahoo.com',
                    author_image: '',
                    author_role: 'صانعة محتوى',
                    content: 'خدمة سريعة ولكن أتمنى إضافة خيارات دفع أكثر في المستقبل. عموماً جودة المنتجات ممتازة جداً.',
                    rating: 4,
                    verified: false,
                    status: 'pending',
                    created_at: new Date(Date.now() - 86400000 * 1).toISOString()
                },
                {
                    id: 201,
                    wall_id: 2,
                    author_name: 'طارق الإدريسي',
                    author_email: 'tariq@cloudtech.ma',
                    author_image: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=120&auto=format&fit=crop&q=80',
                    author_role: 'مؤسس ومدير تنفيذي',
                    content: 'منصة سحاب اختصرت علينا أكثر من 40% من الوقت المهدور في الاجتماعات ومتابعة المهام. الواجهة سريعة وجميلة وتعمل بسلاسة على كل الأجهزة.',
                    rating: 5,
                    verified: true,
                    status: 'approved',
                    created_at: new Date(Date.now() - 86400000 * 3).toISOString()
                },
                {
                    id: 202,
                    wall_id: 2,
                    author_name: 'مريم الصقلي',
                    author_email: 'meryem.s@fintech.io',
                    author_image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=120&auto=format&fit=crop&q=80',
                    author_role: 'قائدة فريق المنتجات',
                    content: 'الواجهة البسيطة والأداء الصاروخي يجعلان سحاب الخيار الأفضل لأي فريق يبحث عن إنجاز حقيقي بدون تعقيدات البرامج القديمة.',
                    rating: 5,
                    verified: true,
                    status: 'approved',
                    created_at: new Date(Date.now() - 86400000 * 2).toISOString()
                },
                {
                    id: 301,
                    wall_id: 3,
                    author_name: 'ياسين بوزيد',
                    author_email: 'yassine@apexmedia.com',
                    author_image: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=120&auto=format&fit=crop&q=80',
                    author_role: 'مدير العمليات — Apex Media',
                    content: 'وكالة ريادة قامت بتجديد هويتنا البصرية بالكامل وموقعنا الإلكتروني في وقت قياسي. تفكيرهم الإبداعي واهتمامهم بالتفاصيل مدهش حقاً.',
                    rating: 5,
                    verified: true,
                    status: 'approved',
                    created_at: new Date(Date.now() - 86400000 * 2).toISOString()
                }
            ];
            localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(defaultTestimonials));
        }
    }

    initSeedData();

    const TrustWallStorage = {
        // --- Auth Operations ---
        register(name, email, password) {
            const users = JSON.parse(localStorage.getItem(STORAGE_KEY_USERS) || '[]');
            if (users.some(u => u.email.toLowerCase() === email.toLowerCase())) {
                throw new Error('البريد الإلكتروني مستخدم بالفعل');
            }
            const newUser = {
                id: Date.now(),
                name,
                email,
                password,
                plan: 'pro'
            };
            users.push(newUser);
            localStorage.setItem(STORAGE_KEY_USERS, JSON.stringify(users));

            const token = 'tw_token_' + Math.random().toString(36).substring(2);
            this.setSession(newUser, token);
            return { user: newUser, token };
        },

        login(email, password) {
            const users = JSON.parse(localStorage.getItem(STORAGE_KEY_USERS) || '[]');
            const user = users.find(u => u.email.toLowerCase() === email.toLowerCase() && u.password === password);
            if (!user) {
                throw new Error('البريد الإلكتروني أو كلمة المرور غير صحيحة');
            }
            const token = 'tw_token_' + Math.random().toString(36).substring(2);
            this.setSession(user, token);
            return { user, token };
        },

        demoLogin() {
            const defaultUser = { id: 1, name: 'محمد الزروالي', email: 'demo@trustwall.com', plan: 'pro' };
            const token = 'tw_token_demo_mode';
            this.setSession(defaultUser, token);
            return { user: defaultUser, token };
        },

        setSession(user, token) {
            localStorage.setItem(STORAGE_KEY_CURRENT_USER, JSON.stringify({
                id: user.id,
                name: user.name,
                email: user.email,
                plan: user.plan || 'pro'
            }));
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

        // --- Walls Operations ---
        getWalls() {
            return JSON.parse(localStorage.getItem(STORAGE_KEY_WALLS) || '[]');
        },

        getUserWalls() {
            const user = this.getCurrentUser();
            const walls = this.getWalls();
            if (!user) return walls;
            const userWalls = walls.filter(w => w.user_id === user.id);
            return userWalls.length > 0 ? userWalls : walls;
        },

        getWallBySlug(slug) {
            if (!slug) return null;
            const walls = this.getWalls();
            return walls.find(w => w.slug.toLowerCase() === slug.toLowerCase()) || null;
        },

        getWallById(id) {
            const walls = this.getWalls();
            return walls.find(w => w.id === Number(id)) || null;
        },

        createWall({ title, description, color, welcome_message, slug }) {
            const user = this.getCurrentUser() || { id: 1 };
            const walls = this.getWalls();
            
            let finalSlug = slug ? slug.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '-') : generateSlug('wall');
            if (walls.some(w => w.slug === finalSlug)) {
                finalSlug = generateSlug('wall');
            }

            const newWall = {
                id: Date.now(),
                user_id: user.id,
                slug: finalSlug,
                title: title.trim(),
                description: (description || '').trim(),
                color: color || '#0071e3',
                welcome_message: (welcome_message || 'شكراً لك على مشاركة تجربتك معنا!').trim(),
                created_at: new Date().toISOString()
            };

            walls.unshift(newWall);
            localStorage.setItem(STORAGE_KEY_WALLS, JSON.stringify(walls));
            return newWall;
        },

        deleteWall(id) {
            let walls = this.getWalls();
            walls = walls.filter(w => w.id !== Number(id));
            localStorage.setItem(STORAGE_KEY_WALLS, JSON.stringify(walls));

            let testimonials = this.getAllTestimonials();
            testimonials = testimonials.filter(t => t.wall_id !== Number(id));
            localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(testimonials));
        },

        // --- Testimonials Operations ---
        getAllTestimonials() {
            return JSON.parse(localStorage.getItem(STORAGE_KEY_TESTIMONIALS) || '[]');
        },

        getWallTestimonials(wallId, filterStatus = null) {
            const testimonials = this.getAllTestimonials();
            return testimonials.filter(t => {
                const match = t.wall_id === Number(wallId);
                if (!filterStatus || filterStatus === 'all') return match;
                return match && t.status === filterStatus;
            });
        },

        addTestimonial(slug, { author_name, author_email, author_image, author_role, content, rating }) {
            const wall = this.getWallBySlug(slug);
            if (!wall) throw new Error('الجدار المطلوب غير موجود');

            const testimonials = this.getAllTestimonials();
            const newTestimonial = {
                id: Date.now(),
                wall_id: wall.id,
                author_name: author_name.trim(),
                author_email: (author_email || '').trim(),
                author_image: author_image || '',
                author_role: (author_role || 'عميل موثق').trim(),
                content: content.trim(),
                rating: Math.min(5, Math.max(1, Number(rating) || 5)),
                verified: true,
                status: 'pending',
                created_at: new Date().toISOString()
            };

            testimonials.unshift(newTestimonial);
            localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(testimonials));
            return newTestimonial;
        },

        updateTestimonialStatus(id, status) {
            const testimonials = this.getAllTestimonials();
            const target = testimonials.find(t => t.id === Number(id));
            if (target) {
                target.status = status;
                localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(testimonials));
            }
            return target;
        },

        deleteTestimonial(id) {
            let testimonials = this.getAllTestimonials();
            testimonials = testimonials.filter(t => t.id !== Number(id));
            localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(testimonials));
        },

        // --- Analytics & Stats ---
        getAnalytics() {
            const user = this.getCurrentUser();
            const walls = this.getUserWalls();
            const wallIds = walls.map(w => w.id);
            const allTestimonials = this.getAllTestimonials().filter(t => wallIds.includes(t.wall_id));

            const totalWalls = walls.length;
            const totalReviews = allTestimonials.length;
            const pendingReviews = allTestimonials.filter(t => t.status === 'pending').length;
            const approvedReviews = allTestimonials.filter(t => t.status === 'approved').length;

            const totalRating = allTestimonials.reduce((acc, t) => acc + (t.rating || 5), 0);
            const avgRating = totalReviews > 0 ? (totalRating / totalReviews).toFixed(1) : '5.0';
            const satisfactionRate = totalReviews > 0 ? Math.round((approvedReviews / totalReviews) * 100) : 100;

            return {
                totalWalls,
                totalReviews,
                pendingReviews,
                approvedReviews,
                avgRating,
                satisfactionRate
            };
        },

        // --- JSON Backup / Restore ---
        exportData() {
            return JSON.stringify({
                version: '2.0',
                exportDate: new Date().toISOString(),
                walls: this.getWalls(),
                testimonials: this.getAllTestimonials()
            }, null, 2);
        },

        importData(jsonString) {
            try {
                const data = JSON.parse(jsonString);
                if (data.walls && Array.isArray(data.walls)) {
                    localStorage.setItem(STORAGE_KEY_WALLS, JSON.stringify(data.walls));
                }
                if (data.testimonials && Array.isArray(data.testimonials)) {
                    localStorage.setItem(STORAGE_KEY_TESTIMONIALS, JSON.stringify(data.testimonials));
                }
                return true;
            } catch (err) {
                console.error('Import failed:', err);
                return false;
            }
        },

        resetToDefaults() {
            localStorage.removeItem(STORAGE_KEY_USERS);
            localStorage.removeItem(STORAGE_KEY_WALLS);
            localStorage.removeItem(STORAGE_KEY_TESTIMONIALS);
            initSeedData();
        },

        // --- Helpers ---
        getSlugFromUrl() {
            const urlParams = new URLSearchParams(window.location.search);
            const slugFromParam = urlParams.get('slug');
            if (slugFromParam) return slugFromParam;

            if (window.location.hash && window.location.hash.length > 1) {
                return window.location.hash.substring(1);
            }

            const parts = window.location.pathname.split('/').filter(Boolean);
            const lastPart = parts[parts.length - 1] || '';
            if (lastPart && !lastPart.endsWith('.html') && !['wall', 'submit', 'embed'].includes(lastPart)) {
                return lastPart;
            }
            return 'elite-store'; // Default active wall
        },

        fileToBase64(file, maxWidth = 400) {
            return new Promise((resolve, reject) => {
                if (!file) {
                    resolve('');
                    return;
                }
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = (event) => {
                    const img = new Image();
                    img.src = event.target.result;
                    img.onload = () => {
                        const elem = document.createElement('canvas');
                        const scaleFactor = Math.min(1, maxWidth / img.width);
                        elem.width = img.width * scaleFactor;
                        elem.height = img.height * scaleFactor;
                        const ctx = elem.getContext('2d');
                        ctx.drawImage(img, 0, 0, elem.width, elem.height);
                        resolve(elem.toDataURL('image/jpeg', 0.85));
                    };
                    img.onerror = () => resolve(event.target.result);
                };
                reader.onerror = error => reject(error);
            });
        }
    };

    window.TrustWallStorage = TrustWallStorage;
})(window);
