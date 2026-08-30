const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'trustwall-secret-key-change-in-production';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname)));
app.use(express.static(path.join(__dirname, 'public')));

// Ensure uploads directory exists
const uploadsDir = path.join(__dirname, 'public', 'uploads');
if (!fs.existsSync(uploadsDir)) {
    fs.mkdirSync(uploadsDir, { recursive: true });
}

// Multer config for image uploads
const storage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, uploadsDir),
    filename: (req, file, cb) => {
        const uniqueName = uuidv4() + path.extname(file.originalname);
        cb(null, uniqueName);
    }
});
const upload = multer({ 
    storage,
    limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
    fileFilter: (req, file, cb) => {
        const allowed = ['image/jpeg', 'image/png', 'image/webp'];
        cb(null, allowed.includes(file.mimetype));
    }
});

// Database setup
const dbPath = path.join(__dirname, 'database', 'trustwall.db');
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) console.error('DB Error:', err);
    else console.log('✅ Connected to SQLite');
});

// Create tables
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS walls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        color TEXT DEFAULT '#3b82f6',
        logo TEXT,
        welcome_message TEXT DEFAULT 'شكراً لك على مشاركة تجربتك معنا!',
        is_public INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS testimonials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wall_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        author_email TEXT,
        author_image TEXT,
        content TEXT NOT NULL,
        rating INTEGER DEFAULT 5,
        video_url TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (wall_id) REFERENCES walls(id)
    )`);
});

// Auth middleware
const authenticate = (req, res, next) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Unauthorized' });

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) return res.status(403).json({ error: 'Invalid token' });
        req.user = user;
        next();
    });
};

// ========== AUTH ROUTES ==========

// Register
app.post('/api/auth/register', async (req, res) => {
    const { name, email, password } = req.body;
    if (!name || !email || !password) {
        return res.status(400).json({ error: 'جميع الحقول مطلوبة' });
    }

    const hashed = await bcrypt.hash(password, 10);
    db.run('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', 
        [name, email, hashed], 
        function(err) {
            if (err) {
                if (err.message.includes('UNIQUE')) {
                    return res.status(400).json({ error: 'البريد الإلكتروني مستخدم بالفعل' });
                }
                return res.status(500).json({ error: err.message });
            }
            const token = jwt.sign({ id: this.lastID, email, name }, JWT_SECRET);
            res.json({ token, user: { id: this.lastID, name, email } });
        }
    );
});

// Login
app.post('/api/auth/login', (req, res) => {
    const { email, password } = req.body;
    db.get('SELECT * FROM users WHERE email = ?', [email], async (err, user) => {
        if (err || !user) return res.status(400).json({ error: 'بيانات الدخول غير صحيحة' });

        const valid = await bcrypt.compare(password, user.password);
        if (!valid) return res.status(400).json({ error: 'بيانات الدخول غير صحيحة' });

        const token = jwt.sign({ id: user.id, email: user.email, name: user.name }, JWT_SECRET);
        res.json({ token, user: { id: user.id, name: user.name, email: user.email } });
    });
});

// Get current user
app.get('/api/auth/me', authenticate, (req, res) => {
    res.json(req.user);
});

// ========== WALL ROUTES ==========

// Create wall
app.post('/api/walls', authenticate, (req, res) => {
    const { title, description, color, welcome_message } = req.body;
    const slug = uuidv4().slice(0, 8);

    db.run(
        'INSERT INTO walls (user_id, slug, title, description, color, welcome_message) VALUES (?, ?, ?, ?, ?, ?)',
        [req.user.id, slug, title, description, color || '#3b82f6', welcome_message],
        function(err) {
            if (err) return res.status(500).json({ error: err.message });
            res.json({ id: this.lastID, slug, title });
        }
    );
});

// Get user's walls
app.get('/api/walls', authenticate, (req, res) => {
    db.all('SELECT * FROM walls WHERE user_id = ? ORDER BY created_at DESC', [req.user.id], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(rows);
    });
});

// Get single wall (public)
app.get('/api/walls/:slug', (req, res) => {
    db.get('SELECT * FROM walls WHERE slug = ?', [req.params.slug], (err, wall) => {
        if (err || !wall) return res.status(404).json({ error: 'Wall not found' });

        db.all('SELECT * FROM testimonials WHERE wall_id = ? AND status = "approved" ORDER BY created_at DESC', 
            [wall.id], (err, testimonials) => {
                res.json({ wall, testimonials });
            }
        );
    });
});

// Update wall
app.put('/api/walls/:id', authenticate, (req, res) => {
    const { title, description, color, welcome_message } = req.body;
    db.run(
        'UPDATE walls SET title=?, description=?, color=?, welcome_message=? WHERE id=? AND user_id=?',
        [title, description, color, welcome_message, req.params.id, req.user.id],
        function(err) {
            if (err) return res.status(500).json({ error: err.message });
            res.json({ updated: this.changes });
        }
    );
});

// Delete wall
app.delete('/api/walls/:id', authenticate, (req, res) => {
    db.run('DELETE FROM walls WHERE id=? AND user_id=?', [req.params.id, req.user.id], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ deleted: this.changes });
    });
});

// ========== TESTIMONIAL ROUTES ==========

// Submit testimonial (public)
app.post('/api/walls/:slug/testimonials', upload.single('image'), (req, res) => {
    const { author_name, author_email, content, rating } = req.body;
    const image = req.file ? '/uploads/' + req.file.filename : null;

    db.get('SELECT id FROM walls WHERE slug = ?', [req.params.slug], (err, wall) => {
        if (err || !wall) return res.status(404).json({ error: 'Wall not found' });

        db.run(
            'INSERT INTO testimonials (wall_id, author_name, author_email, author_image, content, rating) VALUES (?, ?, ?, ?, ?, ?)',
            [wall.id, author_name, author_email, image, content, parseInt(rating) || 5],
            function(err) {
                if (err) return res.status(500).json({ error: err.message });
                res.json({ success: true, id: this.lastID });
            }
        );
    });
});

// Get pending testimonials for admin
app.get('/api/walls/:id/testimonials/pending', authenticate, (req, res) => {
    db.get('SELECT * FROM walls WHERE id=? AND user_id=?', [req.params.id, req.user.id], (err, wall) => {
        if (err || !wall) return res.status(403).json({ error: 'Unauthorized' });

        db.all('SELECT * FROM testimonials WHERE wall_id = ? ORDER BY created_at DESC', [req.params.id], (err, rows) => {
            if (err) return res.status(500).json({ error: err.message });
            res.json(rows);
        });
    });
});

// Update testimonial status
app.put('/api/testimonials/:id/status', authenticate, (req, res) => {
    const { status } = req.body; // 'approved' or 'rejected'

    db.get(`SELECT t.*, w.user_id FROM testimonials t JOIN walls w ON t.wall_id = w.id WHERE t.id = ?`, 
        [req.params.id], (err, row) => {
            if (err || !row || row.user_id !== req.user.id) {
                return res.status(403).json({ error: 'Unauthorized' });
            }

            db.run('UPDATE testimonials SET status = ? WHERE id = ?', [status, req.params.id], function(err) {
                if (err) return res.status(500).json({ error: err.message });
                res.json({ updated: this.changes });
            });
        }
    );
});

// Delete testimonial
app.delete('/api/testimonials/:id', authenticate, (req, res) => {
    db.get(`SELECT t.*, w.user_id FROM testimonials t JOIN walls w ON t.wall_id = w.id WHERE t.id = ?`, 
        [req.params.id], (err, row) => {
            if (err || !row || row.user_id !== req.user.id) {
                return res.status(403).json({ error: 'Unauthorized' });
            }

            db.run('DELETE FROM testimonials WHERE id = ?', [req.params.id], function(err) {
                if (err) return res.status(500).json({ error: err.message });
                res.json({ deleted: this.changes });
            });
        }
    );
});

// ========== EMBED WIDGET ==========

// Get embed code
app.get('/api/walls/:slug/embed', (req, res) => {
    db.get('SELECT * FROM walls WHERE slug = ?', [req.params.slug], (err, wall) => {
        if (err || !wall) return res.status(404).json({ error: 'Wall not found' });

        db.all('SELECT * FROM testimonials WHERE wall_id = ? AND status = "approved" ORDER BY created_at DESC', 
            [wall.id], (err, testimonials) => {
                res.json({ wall, testimonials });
            }
        );
    });
});

// ========== PAGES ==========

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, 'dashboard.html'));
});

app.get('/wall/:slug', (req, res) => {
    res.sendFile(path.join(__dirname, 'wall.html'));
});

app.get('/submit/:slug', (req, res) => {
    res.sendFile(path.join(__dirname, 'submit.html'));
});

app.get('/embed/:slug', (req, res) => {
    res.sendFile(path.join(__dirname, 'embed.html'));
});

app.get('/login', (req, res) => {
    res.sendFile(path.join(__dirname, 'login.html'));
});

app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, 'register.html'));
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 TrustWall running on http://localhost:${PORT}`);
});
