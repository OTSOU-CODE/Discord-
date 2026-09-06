# 🚌 Categories Game (أتوبيس كومبلي / Le Petit Bac)

A modern, real-time multiplayer word game **Categories (أتوبيس كومبلي)** engineered to run **100% natively on GitHub infrastructure** with zero external websites, accounts, or hosting providers.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new)

---

## ✨ Features

- **100% Native GitHub Infrastructure**:
  - **GitHub Codespaces**: 1-click cloud multiplayer server running on GitHub with automated `.devcontainer` configuration and public HTTPS port forwarding (`*.app.github.dev`). Zero external services needed.
  - **GitHub Pages**: Automated CI/CD pipeline via GitHub Actions (`deploy.yml`) for static web deployment.
  - **In-Browser Solo Practice**: Full offline practice mode runnable directly on GitHub Pages with client-side scoring evaluation and zero server dependencies.
- **Real-Time Multiplayer Engine**: Authoritative countdown timer, in-memory room management, live typing progress indicator, and instant "STOP" freeze mechanism.
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
    - **20 points**: Solo answer bonus (only one player in the lobby had a valid answer).
    - **0 points**: Blank, rejected by vote, or starting with the wrong letter.
- **Paper-Notebook Luxury Aesthetic**: Warm cream stationery background (`#FDFBF7`), subtle ruled lines, tactile buttons, sound effects (Web Audio API synthesizers), and canvas confetti victory podium.
- **Mobile QR Code & Frictionless Join**: QR code and invite link automatically propagate room codes and Codespaces public URLs so friends on mobile phones or laptops join with 1 click.

---

## 🐙 100% Native GitHub Hosting

No third-party hosts, no Render, no Railway, no Cloudflare, and no external websites. Everything runs strictly on GitHub.

### Method 1: GitHub Codespaces (1-Click Cloud Multiplayer — Recommended)

Every GitHub user receives **60 free hours per month** of GitHub Codespaces.

1. Click the badge: [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new)  
   *(Or in your repository on GitHub, click the green **Code** button &gt; **Codespaces** &gt; **Create codespace on main**)*.
2. GitHub automatically:
   - Sets up the Node.js 20 container environment using `.devcontainer/devcontainer.json`.
   - Runs `npm install && npm run build`.
   - Starts the game server on port `3000`.
   - Sets port `3000` visibility to **Public** (`*.app.github.dev`).
3. GitHub automatically opens the game in your browser at:
   ```text
   https://<your-codespace-name>-3000.app.github.dev
   ```
4. **Play with Friends**: Click **Create Room**, then click **Wi-Fi / QR Share**. Share the generated link or QR code with friends anywhere in the world—they connect and play immediately!

---

### Method 2: GitHub Pages (Frontend) + GitHub Codespaces (Backend)

You can also host the static web app on **GitHub Pages** and connect it to your GitHub Codespace:

1. In your GitHub repository, go to **Settings** &gt; **Pages**.
2. Under **Build and deployment** &gt; **Source**, select **GitHub Actions**.
3. The included `.github/workflows/deploy.yml` workflow will automatically run tests, build the frontend, and deploy it live to:
   ```text
   https://<YOUR_USERNAME>.github.io/<YOUR_REPO_NAME>/
   ```
4. In the GitHub Pages app, open **Server Settings** (top-right server icon) and paste your Codespace URL (`https://<your-codespace>-3000.app.github.dev`).
5. Room invite links and QR codes will automatically embed `?server=https://...` so friends joining don't have to configure anything!

---

### Method 3: In-Browser Solo Practice (GitHub Pages / Offline)

Want to play or train solo without starting any server?

1. Open the game on GitHub Pages or locally.
2. In the home card, select the **Solo Practice (تدريب فردي)** tab.
3. Configure your language, round time, and number of rounds, then click **Start Solo Practice**.
4. The client-side engine rolls letters, runs the timer, and evaluates all 9 categories automatically directly in your browser.

---

### Method 4: Local PC & Wi-Fi (Home / Office)

Run the server on your own computer:

```bash
# 1. Install dependencies
npm install

# 2. Build frontend
npm run build

# 3. Start server
npm start
```

The server binds to `0.0.0.0:3000` and displays your local network addresses:
```text
======================================================
🚌 Categories Game (أتوبيس كومبلي) Server Running!
======================================================
📡 Bound:        http://0.0.0.0:3000
💻 Local:        http://localhost:3000
📱 Wi-Fi / LAN:  http://192.168.1.X:3000
======================================================
```
Friends connected to the same Wi-Fi router can scan the in-game QR code or navigate to `http://192.168.1.X:3000` to play together.

---

## 🧪 Running Automated Tests

Run the full automated test suite (unit tests, engine tests, GitHub hosting verification, and real-time Socket.io integration flow):

```bash
npm test
```

---

## 📂 Project Structure

```
Categories/
├── .devcontainer/
│   ├── devcontainer.json     # GitHub Codespaces config with automated public port 3000 forwarding
│   └── on-start.sh           # Codespaces background server startup script
├── .github/
│   └── workflows/
│       └── deploy.yml        # GitHub Actions automated test, build & deploy to GitHub Pages
├── .vscode/
│   └── tasks.json            # VS Code / Codespaces auto-tasks for server execution and logs
├── dist/                     # Production build artifacts (served statically by Express on port 3000)
├── server/
│   ├── alphabet.js           # Alphabets, letter pools & text normalizations
│   ├── categories.js         # 9 fixed categories definitions & metadata
│   ├── roomManager.js        # Real-time in-memory state & room lifecycle engine
│   └── scoring.js            # Auto-check & peer voting scoring calculator
├── src/
│   ├── components/
│   │   ├── CarouselRoll.jsx  # 3-second animated rolling letter carousel
│   │   ├── CreateJoinView.jsx# Create room, join room, and Solo Practice notebook card
│   │   ├── GameRoundView.jsx # Live 9-category input grid with STOP trigger
│   │   ├── LeaderboardView.jsx# Scoreboard and round recap
│   │   ├── LobbyView.jsx     # Players list, room settings & host controls
│   │   ├── Navbar.jsx        # App header, room code pill, sound & server toggles
│   │   ├── NetworkModal.jsx  # Wi-Fi / Codespace URL detection & QR code generator
│   │   ├── PodiumModal.jsx   # Winner podium & canvas confetti celebration
│   │   ├── ServerModal.jsx   # 100% GitHub native hosting & Codespaces connection modal
│   │   └── VotingReviewView.jsx# Peer voting & answer review screen
│   ├── constants/
│   │   ├── categories.js     # Frontend category definitions and icons
│   │   └── translations.js   # Arabic, English, and French dictionaries
│   ├── utils/
│   │   └── soundEffects.js   # Web Audio API synthesizers (bells, alarms, buzzers)
│   ├── App.jsx               # Root React application, state router & Solo engine
│   ├── index.css             # Tailwind directives & paper stationery styles
│   ├── main.jsx              # DOM entry point
│   └── socket.js             # Socket.io client wrapper & Codespaces auto-detection
├── test/
│   ├── engine.test.js        # Unit tests for scoring & alphabet normalization
│   ├── githubHosting.test.js # Unit tests for GitHub Codespaces URL normalization & detection
│   ├── integration.test.js   # Full HTTP, CORS, Codespaces headers & Socket.io integration test
│   └── roomManager.test.js   # Room lifecycle and multiplayer state tests
├── .gitignore                # Excludes node_modules, dist, and environment files
├── Dockerfile                # Standard container definition
├── index.html                # HTML entry template with Google Fonts (Cairo & Outfit)
├── package.json              # Project dependencies & scripts
├── postcss.config.js         # PostCSS configuration
├── server.js                 # Express + Socket.io server with Codespaces detection
├── tailwind.config.js        # Custom Tailwind paper theme configuration
└── vite.config.js            # Vite build with relative base path & dev proxy
```
