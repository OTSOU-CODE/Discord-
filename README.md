# 🚌 Categories Game (أتوبيس كومبلي / Le Petit Bac)

A modern, self-hosted, real-time multiplayer web app for the classic word game **Categories (أتوبيس كومبلي)**. Built to run locally on your PC via Node.js and be accessible to friends over local Wi-Fi or reverse-proxy tunnels (like Cloudflare Tunnel or Ngrok).

---

## ✨ Features

- **Real-Time Multiplayer Engine**: Authoritative server-synced countdown timer, in-memory room management, live typing progress indicator, and instant "STOP" freeze mechanism.
- **Reverse Proxy & Tunnel Ready**: Seamless WebSocket CORS, headers, and HTTPS support designed out-of-the-box for Cloudflare Tunnels (`*.trycloudflare.com`) and Ngrok (`*.ngrok-free.app`).
- **9 Fixed Categories**:
  1. 👤 Boy's Name (ولد)
  2. ❤️ Girl's Name (بنت)
  3. 🐾 Animal (حيوان)
  4. 🍎 Fruit / Vegetable (نبات / خضر وفواكه)
  5. 📦 Object / Inanimate (جماد)
  6. 🏙️ City (مدينة)
  7. 🌍 Country (دولة)
  8. 💼 Profession (مهنة)
  9. 🎨 Color (لون)
- **Alphabet & Normalization Engine**:
  - Languages: Arabic (العربية), English, French (Français).
  - Dynamic RTL / LTR switching with typography optimized for Arabic (Cairo font) and Latin (Outfit font).
  - Intelligent Arabic normalization: handles *Al-* (`ال`) prefix matching, unifies alifs (`أ`, `إ`, `آ` $\rightarrow$ `ا`), taa marbuta (`ة` $\rightarrow$ `ه`), yaa (`ى` $\rightarrow$ `ي`), and strips diacritics / tashkeel.
  - Rare letter toggles (ض, ظ, غ in Arabic; Q, X, Z in English/French).
  - 3-second animated rolling letter carousel before each round starts.
- **Peer Voting & Scoring Phase**:
  - Category-by-category shared review screen with auto-check matching.
  - Interactive peer voting (👍 Approve / 👎 Reject) with real-time majority decision.
  - Official Scoring Rules:
    - **10 points**: Valid unique answer.
    - **5 points**: Valid answer shared by two or more players.
    - **20 points**: Only one player in the entire lobby provided a valid answer for that category!
    - **0 points**: Blank, rejected by vote, or starting with the wrong letter.
- **Paper-Notebook Luxury Aesthetic**: Warm cream stationery background (`#FDFBF7`), subtle ruled lines, tactile buttons, sound effects (Web Audio API synthesizers), and canvas confetti victory podium.
- **Local Wi-Fi QR Code & Network Sharing**: Built-in modal detects your LAN IP and generates a mobile-scannable QR code to join immediately from smartphones on the same Wi-Fi.

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
npm install
```

### 2. Build Frontend
```bash
npm run build
```

### 3. Start the Server
```bash
npm start
```
The server will bind to `0.0.0.0:3000` and display your local and Wi-Fi addresses in the terminal:
```text
📡 Bound:        http://0.0.0.0:3000
💻 Local:        http://localhost:3000
📱 Wi-Fi / LAN:  http://192.168.1.X:3000
```

---

## 🐙 Hosting on GitHub (Frontend + Backend)

You can host the game frontend on **GitHub Pages** for free, and connect it to a free backend host (Render, Railway) or your local PC tunnel.

### Step 1: Push Repository to GitHub
1. Create a new repository on [GitHub](https://github.com/new).
2. Link your local project and push:
   ```bash
   git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git
   git add .
   git commit -m "feat: Categories multiplayer game with GitHub Pages support"
   git branch -M main
   git push -u origin main
   ```

### Step 2: Enable GitHub Pages (Automated via GitHub Actions)
1. On GitHub, go to your repository **Settings** > **Pages**.
2. Under **Build and deployment** > **Source**, choose **GitHub Actions**.
3. The included `.github/workflows/deploy.yml` workflow automatically runs the test suite, builds the frontend with relative base assets, and deploys it live to `https://<YOUR_USERNAME>.github.io/<YOUR_REPO_NAME>/`!

### Step 3: Run the Multiplayer Backend Server
GitHub Pages serves static web files. To run the real-time Socket.io multiplayer engine:

#### Option A: Free Cloud Deployment (Render.com)
1. Sign up for free at [Render.com](https://render.com).
2. Click **New +** > **Blueprint**, and select your GitHub repository.
3. Render automatically uses the included `render.yaml` specification to launch your server for free!
4. Copy your backend URL (e.g. `https://categories-game.onrender.com`).

#### Option B: Free PC Tunnel (Cloudflare Tunnel)
- Start the server on your PC:
  ```bash
  npm start
  ```
- In another terminal:
  ```bash
  cloudflared tunnel --url http://localhost:3000
  ```
- Copy the public HTTPS URL (e.g. `https://my-words.trycloudflare.com`).

### Step 4: Frictionless Invites for Players
- In your GitHub Pages web app, click the **Server Settings** icon in the navbar (or the auto-prompt) and enter your backend URL.
- When you create a room and click **Wi-Fi / QR Share**, the invite link automatically embeds `?join=ROOMCODE&server=YOUR_BACKEND_URL`.
- **Friends who open the link or scan the QR code connect directly with ZERO manual configuration required!**

---

## 🌐 Playing with Friends

### Option A: Local Wi-Fi (Same Network)
1. Ensure your PC and friends' phones/laptops are connected to the same Wi-Fi router.
2. Open `http://localhost:3000` on your PC and click **Create Room**.
3. In the lobby, click **Wi-Fi / QR Share** (or friends can type `http://<YOUR_LOCAL_IP>:3000` and enter the 5-character room code).

### Option B: Internet via Cloudflare Tunnel (Recommended, Free & No Port Forwarding)
1. Download [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).
2. In a separate terminal, run:
   ```bash
   cloudflared tunnel --url http://localhost:3000
   ```
3. Share the generated HTTPS URL (e.g. `https://random-words.trycloudflare.com`) with your friends anywhere in the world!

### Option C: Internet via Ngrok
```bash
ngrok http 3000
```

---

## 🧪 Running Automated Tests

Run the built-in Node test runner:
```bash
node --test test/*.test.js
```

---

## 📂 Project Structure

```
Categories/
├── .github/
│   └── workflows/
│       └── deploy.yml        # GitHub Actions automated test, build & deploy to GitHub Pages
├── dist/                     # Built production client assets (HTML, CSS, JS)
├── server/
│   ├── alphabet.js           # Alphabets, letter pools & text normalizations
│   ├── categories.js         # 9 fixed categories definitions & metadata
│   ├── roomManager.js        # Real-time in-memory state & room lifecycle engine
│   └── scoring.js            # Auto-check & peer voting scoring calculator
├── src/
│   ├── components/
│   │   ├── CarouselRoll.jsx  # 3-second animated rolling letter carousel
│   │   ├── CreateJoinView.jsx# Create room & join room notebook card
│   │   ├── GameRoundView.jsx # Live 9-category input grid with STOP trigger
│   │   ├── LeaderboardView.jsx# Scoreboard and round recap
│   │   ├── LobbyView.jsx     # Players list, room settings & host controls
│   │   ├── Navbar.jsx        # App header, room code pill, sound & server toggles
│   │   ├── NetworkModal.jsx  # Wi-Fi IP address detection & QR code generator
│   │   ├── PodiumModal.jsx   # Winner podium & canvas confetti celebration
│   │   ├── ServerModal.jsx   # Backend server connection & cloud deployment modal
│   │   └── VotingReviewView.jsx# Peer voting & answer review screen
│   ├── constants/
│   │   ├── categories.js     # Frontend category definitions and icons
│   │   └── translations.js   # Arabic, English, and French dictionaries
│   ├── utils/
│   │   └── soundEffects.js   # Web Audio API synthesizers (bells, alarms, buzzers)
│   ├── App.jsx               # Root React application & state router
│   ├── index.css             # Tailwind directives & paper stationery styles
│   ├── main.jsx              # DOM entry point
│   └── socket.js             # Socket.io client wrapper, auto-detection & reconnection
├── test/
│   ├── engine.test.js        # Unit tests for scoring & alphabet normalization
│   ├── githubHosting.test.js # Unit tests for URL normalization
│   ├── integration.test.js   # Full HTTP, CORS & Socket.io integration test
│   └── roomManager.test.js   # Room lifecycle and multiplayer state tests
├── .gitignore                # Excludes node_modules, dist, and environment files
├── Dockerfile                # Docker container definition for cloud deployment
├── Procfile                  # Railway / Heroku deployment process file
├── render.yaml               # Render Blueprint for 1-click cloud server deployment
├── index.html                # HTML entry template with Google Fonts (Cairo & Outfit)
├── package.json              # Project dependencies & scripts
├── postcss.config.js         # PostCSS configuration
├── server.js                 # Express + Socket.io server binding to 0.0.0.0:3000
├── tailwind.config.js        # Custom Tailwind paper theme configuration
└── vite.config.js            # Vite build with relative base path & dev proxy
```
