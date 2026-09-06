import React, { useState, useEffect } from 'react';
import { PlusCircle, LogIn, Globe2, Clock, Hash, Sparkles, AlertCircle, Gamepad2 } from 'lucide-react';
import { playClick } from '../utils/soundEffects';
import { isStaticHost, hasConfiguredServer } from '../socket';

export function CreateJoinView({ 
  onCreateRoom, 
  onJoinRoom, 
  onStartSolo,
  t, 
  currentLang, 
  onLangChange,
  initialRoomCode = ''
}) {
  const [mode, setMode] = useState(initialRoomCode ? 'join' : 'create');
  const [playerName, setPlayerName] = useState(() => localStorage.getItem('categories_player_name') || '');
  const [roomCode, setRoomCode] = useState(initialRoomCode);
  const [roundDuration, setRoundDuration] = useState(60);
  const [totalRounds, setTotalRounds] = useState(5);
  const [includeRare, setIncludeRare] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (initialRoomCode) {
      setRoomCode(initialRoomCode.toUpperCase());
      setMode('join');
    }
  }, [initialRoomCode]);

  const handleSolo = (e) => {
    e.preventDefault();
    if (!playerName.trim()) {
      setErrorMsg('الرجاء إدخال اسمك أولاً / Please enter your name');
      return;
    }
    setErrorMsg('');
    playClick();

    onStartSolo?.({
      playerName: playerName.trim(),
      settings: {
        lang: currentLang,
        roundDuration: Number(roundDuration),
        totalRounds: Number(totalRounds),
        includeRare
      }
    });
  };

  const handleCreate = (e) => {
    e.preventDefault();
    if (!playerName.trim()) {
      setErrorMsg('الرجاء إدخال اسمك أولاً / Please enter your name');
      return;
    }
    setErrorMsg('');
    setIsSubmitting(true);
    playClick();

    onCreateRoom({
      playerName: playerName.trim(),
      settings: {
        lang: currentLang,
        roundDuration: Number(roundDuration),
        totalRounds: Number(totalRounds),
        includeRare
      }
    }, (err) => {
      setIsSubmitting(false);
      if (err) setErrorMsg(err);
    });
  };

  const handleJoin = (e) => {
    e.preventDefault();
    if (!playerName.trim()) {
      setErrorMsg('الرجاء إدخال اسمك أولاً / Please enter your name');
      return;
    }
    if (!roomCode.trim() || roomCode.trim().length !== 5) {
      setErrorMsg('رمز الغرفة يجب أن يتكون من 5 أحرف / Room code must be 5 characters');
      return;
    }
    setErrorMsg('');
    setIsSubmitting(true);
    playClick();

    onJoinRoom({
      playerName: playerName.trim(),
      roomCode: roomCode.trim().toUpperCase()
    }, (err) => {
      setIsSubmitting(false);
      if (err) setErrorMsg(err);
    });
  };

  return (
    <div className="w-full max-w-md mx-auto my-6 px-4">
      {/* Paper Card Container */}
      <div className="bg-paper-50 border-2 border-paper-border rounded-3xl p-6 sm:p-8 shadow-notebook relative overflow-hidden">
        
        {/* Decorative ruled lines & notebook punched hole visual */}
        <div className="absolute top-4 start-4 w-3 h-3 rounded-full bg-paper-300 border border-paper-400 shadow-inner" />
        <div className="absolute top-4 end-4 w-3 h-3 rounded-full bg-paper-300 border border-paper-400 shadow-inner" />

        {/* Tab Toggle: Create vs Join vs Solo */}
        <div className="flex bg-paper-200 p-1 rounded-2xl mb-6 border border-paper-border shadow-inner">
          <button
            type="button"
            onClick={() => {
              playClick();
              setMode('create');
              setErrorMsg('');
            }}
            className={`flex-1 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-1.5 transition ${
              mode === 'create'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'text-ink-600 hover:text-ink-900'
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>{t.createRoom}</span>
          </button>
          <button
            type="button"
            onClick={() => {
              playClick();
              setMode('join');
              setErrorMsg('');
            }}
            className={`flex-1 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-1.5 transition ${
              mode === 'join'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'text-ink-600 hover:text-ink-900'
            }`}
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>{t.joinRoom}</span>
          </button>
          <button
            type="button"
            onClick={() => {
              playClick();
              setMode('solo');
              setErrorMsg('');
            }}
            className={`flex-1 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-1.5 transition ${
              mode === 'solo'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'text-ink-600 hover:text-ink-900'
            }`}
          >
            <Gamepad2 className="w-3.5 h-3.5" />
            <span>{t.soloPracticeTitle || 'Solo'}</span>
          </button>
        </div>

        {/* Error Banner */}
        {errorMsg && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2 animate-in fade-in">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* GitHub Pages unconfigured server banner suggestion */}
        {isStaticHost() && !hasConfiguredServer() && mode !== 'solo' && (
          <div className="mb-4 bg-amber-50 border border-amber-300 rounded-2xl p-3 text-xs text-amber-900 flex items-start gap-2.5">
            <Sparkles className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold block mb-0.5">
                {currentLang === 'ar' ? '💡 هل تريد اللعب فوراً بدون خادم؟' : currentLang === 'fr' ? '💡 Jouer immédiatement sans serveur ?' : '💡 Want to play right now without a server?'}
              </span>
              <p className="text-[11px] text-amber-800 leading-relaxed">
                {currentLang === 'ar' 
                  ? 'يمكنك التبديل إلى تبويب "تدريب فردي" للعب بدون خادم، أو ربط خادم GitHub Codespaces من إعدادات الخادم.'
                  : currentLang === 'fr'
                    ? 'Basculez sur l’onglet « Mode Solo » pour jouer hors-ligne, ou connectez votre Codespace GitHub.'
                    : 'Switch to the "Solo" tab to play in-browser without a server, or connect a GitHub Codespace in Settings.'}
              </p>
              <button
                type="button"
                onClick={() => {
                  playClick();
                  setMode('solo');
                }}
                className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-bold text-amber-900 underline hover:text-amber-700 cursor-pointer"
              >
                {currentLang === 'ar' ? 'الانتقال إلى التدريب الفردي ←' : currentLang === 'fr' ? 'Passer au Mode Solo →' : 'Switch to Solo Practice →'}
              </button>
            </div>
          </div>
        )}

        {/* Form: Create Room */}
        {mode === 'create' && (
          <form onSubmit={handleCreate} className="space-y-4">
            
            {/* Player Name */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1">
                {t.yourName}
              </label>
              <input
                type="text"
                required
                maxLength={20}
                placeholder={t.enterYourName}
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl input-notebook text-sm font-medium text-ink-900"
              />
            </div>

            {/* Language Selector */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1 flex items-center gap-1.5">
                <Globe2 className="w-3.5 h-3.5 text-amber-700" />
                {t.selectLanguage}
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { code: 'ar', label: 'العربية 🇸🇦' },
                  { code: 'en', label: 'English 🇬🇧' },
                  { code: 'fr', label: 'Français 🇫🇷' }
                ].map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => {
                      playClick();
                      onLangChange(item.code);
                    }}
                    className={`py-2 rounded-xl text-xs font-bold border transition ${
                      currentLang === item.code
                        ? 'bg-amber-100 border-amber-600 text-amber-900'
                        : 'bg-white border-paper-border text-ink-600 hover:bg-paper-100'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Round Duration */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-amber-700" />
                  {t.roundDuration}
                </span>
                <span className="text-amber-800 font-bold">{roundDuration} {t.seconds}</span>
              </label>
              <div className="grid grid-cols-5 gap-1.5">
                {[30, 45, 60, 90, 120].map((dur) => (
                  <button
                    key={dur}
                    type="button"
                    onClick={() => {
                      playClick();
                      setRoundDuration(dur);
                    }}
                    className={`py-1.5 rounded-lg text-xs font-semibold border transition ${
                      roundDuration === dur
                        ? 'bg-amber-100 border-amber-600 text-amber-900'
                        : 'bg-white border-paper-border text-ink-600 hover:bg-paper-100'
                    }`}
                  >
                    {dur}s
                  </button>
                ))}
              </div>
            </div>

            {/* Total Rounds */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Hash className="w-3.5 h-3.5 text-amber-700" />
                  {t.totalRounds}
                </span>
                <span className="text-amber-800 font-bold">{totalRounds} {t.rounds}</span>
              </label>
              <div className="grid grid-cols-4 gap-2">
                {[3, 5, 7, 10].map((rounds) => (
                  <button
                    key={rounds}
                    type="button"
                    onClick={() => {
                      playClick();
                      setTotalRounds(rounds);
                    }}
                    className={`py-1.5 rounded-lg text-xs font-semibold border transition ${
                      totalRounds === rounds
                        ? 'bg-amber-100 border-amber-600 text-amber-900'
                        : 'bg-white border-paper-border text-ink-600 hover:bg-paper-100'
                    }`}
                  >
                    {rounds}
                  </button>
                ))}
              </div>
            </div>

            {/* Include Rare Letters Toggle */}
            <div className="pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={includeRare}
                  onChange={(e) => setIncludeRare(e.target.checked)}
                  className="w-4 h-4 text-amber-600 rounded border-paper-400 focus:ring-amber-500"
                />
                <span className="text-xs text-ink-700 font-medium">
                  {t.includeRareLetters}
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-3 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-2xl font-bold shadow-tactile flex items-center justify-center gap-2 btn-tactile transition"
            >
              <Sparkles className="w-5 h-5" />
              <span>{isSubmitting ? '...' : t.createButton}</span>
            </button>
          </form>
        )}

        {/* Form: Join Room */}
        {mode === 'join' && (
          <form onSubmit={handleJoin} className="space-y-4">
            {/* Player Name */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1">
                {t.yourName}
              </label>
              <input
                type="text"
                required
                maxLength={20}
                placeholder={t.enterYourName}
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl input-notebook text-sm font-medium text-ink-900"
              />
            </div>

            {/* Room Code */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1">
                {t.roomCode}
              </label>
              <input
                type="text"
                required
                maxLength={5}
                placeholder={t.enterRoomCode}
                value={roomCode}
                onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                className="w-full px-4 py-3 rounded-xl input-notebook text-center font-mono font-bold text-xl tracking-widest text-amber-700 uppercase"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-4 py-3 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-2xl font-bold shadow-tactile flex items-center justify-center gap-2 btn-tactile transition"
            >
              <LogIn className="w-5 h-5" />
              <span>{isSubmitting ? '...' : t.joinButton}</span>
            </button>
          </form>
        )}

        {/* Form: Solo Practice (In-Browser / No Server Needed) */}
        {mode === 'solo' && (
          <form onSubmit={handleSolo} className="space-y-4">
            <div className="bg-amber-50 border border-amber-300/80 rounded-xl p-3 text-xs text-amber-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-700 shrink-0" />
              <span>{t.soloPracticeDesc || 'Play and practice offline directly in your browser!'}</span>
            </div>

            {/* Player Name */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1">
                {t.yourName}
              </label>
              <input
                type="text"
                required
                maxLength={20}
                placeholder={t.enterYourName}
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl input-notebook text-sm font-medium text-ink-900"
              />
            </div>

            {/* Language Selector */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1 flex items-center gap-1.5">
                <Globe2 className="w-3.5 h-3.5 text-amber-700" />
                {t.selectLanguage}
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { code: 'ar', label: 'العربية 🇸🇦' },
                  { code: 'en', label: 'English 🇬🇧' },
                  { code: 'fr', label: 'Français 🇫🇷' }
                ].map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => {
                      playClick();
                      onLangChange(item.code);
                    }}
                    className={`py-2 rounded-xl text-xs font-bold border transition ${
                      currentLang === item.code
                        ? 'bg-amber-100 border-amber-600 text-amber-900'
                        : 'bg-white border-paper-border text-ink-600 hover:bg-paper-100'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Round Duration */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-amber-700" />
                  {t.roundDuration}
                </span>
                <span className="text-amber-800 font-bold">{roundDuration} {t.seconds}</span>
              </label>
              <div className="grid grid-cols-5 gap-1.5">
                {[30, 45, 60, 90, 120].map((dur) => (
                  <button
                    key={dur}
                    type="button"
                    onClick={() => {
                      playClick();
                      setRoundDuration(dur);
                    }}
                    className={`py-1.5 rounded-lg text-xs font-semibold border transition ${
                      roundDuration === dur
                        ? 'bg-amber-100 border-amber-600 text-amber-900'
                        : 'bg-white border-paper-border text-ink-600 hover:bg-paper-100'
                    }`}
                  >
                    {dur}s
                  </button>
                ))}
              </div>
            </div>

            {/* Total Rounds */}
            <div>
              <label className="block text-xs font-bold text-ink-700 mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Hash className="w-3.5 h-3.5 text-amber-700" />
                  {t.totalRounds}
                </span>
                <span className="text-amber-800 font-bold">{totalRounds} {t.rounds}</span>
              </label>
              <div className="grid grid-cols-4 gap-2">
                {[3, 5, 7, 10].map((rounds) => (
                  <button
                    key={rounds}
                    type="button"
                    onClick={() => {
                      playClick();
                      setTotalRounds(rounds);
                    }}
                    className={`py-1.5 rounded-lg text-xs font-semibold border transition ${
                      totalRounds === rounds
                        ? 'bg-amber-100 border-amber-600 text-amber-900'
                        : 'bg-white border-paper-border text-ink-600 hover:bg-paper-100'
                    }`}
                  >
                    {rounds}
                  </button>
                ))}
              </div>
            </div>

            {/* Include Rare Letters Toggle */}
            <div className="pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={includeRare}
                  onChange={(e) => setIncludeRare(e.target.checked)}
                  className="w-4 h-4 text-amber-600 rounded border-paper-400 focus:ring-amber-500"
                />
                <span className="text-xs text-ink-700 font-medium">
                  {t.includeRareLetters}
                </span>
              </label>
            </div>

            {/* Start Solo Button */}
            <button
              type="submit"
              className="w-full mt-2 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-2xl font-bold shadow-tactile flex items-center justify-center gap-2 btn-tactile transition"
            >
              <Gamepad2 className="w-5 h-5" />
              <span>{t.soloPracticeTitle || 'Start Solo Practice'}</span>
            </button>
          </form>
        )}

      </div>
    </div>
  );
}
