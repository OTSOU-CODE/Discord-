import React, { useState, useEffect, useRef } from 'react';
import { 
  Clock, 
  OctagonAlert, 
  Users, 
  User, 
  Heart, 
  PawPrint, 
  Apple, 
  Box, 
  Building2, 
  Globe, 
  Briefcase, 
  Palette,
  Sparkles
} from 'lucide-react';
import { CATEGORIES_DEF } from '../constants/categories';
import { playClick, playStopAlarm } from '../utils/soundEffects';

const ICON_MAP = {
  User,
  Heart,
  PawPrint,
  Apple,
  Box,
  Building2,
  Globe,
  Briefcase,
  Palette
};

export function GameRoundView({ 
  room, 
  playerId, 
  letter, 
  roundEndTime, 
  initialDraft,
  onUpdateDraft, 
  onSubmitAnswers,
  onTriggerStop, 
  t 
}) {
  const [draft, setDraft] = useState(() => initialDraft || room?.players?.[playerId]?.draft || {});
  const [timeLeft, setTimeLeft] = useState(room.settings.roundDuration);
  const [hasStopped, setHasStopped] = useState(false);
  const inputRefs = useRef([]);
  const draftRef = useRef(draft);
  const hasStoppedRef = useRef(false);

  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  // Calculate synchronized remaining time from authoritative server timestamp
  useEffect(() => {
    const targetEnd = roundEndTime || room.roundEndTime;
    if (!targetEnd) return;

    const updateTimer = () => {
      const remainingMs = Math.max(0, targetEnd - Date.now());
      const remainingSec = Math.ceil(remainingMs / 1000);
      setTimeLeft(remainingSec);
      if (remainingMs <= 0 && !hasStoppedRef.current) {
        handleStop();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 250);
    return () => clearInterval(interval);
  }, [roundEndTime, room.roundEndTime]);

  // Submit current draft on unmount if not already stopped
  useEffect(() => {
    return () => {
      if (!hasStoppedRef.current && onSubmitAnswers && draftRef.current) {
        onSubmitAnswers(draftRef.current);
      }
    };
  }, [onSubmitAnswers]);

  // Handle input changes and sync draft with server
  const handleInputChange = (catId, value) => {
    if (hasStopped || hasStoppedRef.current) return;
    const nextDraft = { ...draft, [catId]: value };
    setDraft(nextDraft);
    onUpdateDraft(nextDraft);
  };

  // Count filled fields
  const filledCount = CATEGORIES_DEF.filter(c => (draft[c.id] || '').trim().length > 0).length;
  const isAllFilled = filledCount === CATEGORIES_DEF.length;

  // Move to next category input on Enter key, or trigger STOP if on last field and all filled
  const handleKeyDown = (e, index) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const nextIndex = index + 1;
      if (nextIndex < CATEGORIES_DEF.length && inputRefs.current[nextIndex]) {
        inputRefs.current[nextIndex].focus();
      } else if (isAllFilled) {
        handleStop();
      }
    }
  };

  const handleStop = () => {
    if (hasStoppedRef.current) return;
    hasStoppedRef.current = true;
    setHasStopped(true);
    playStopAlarm();
    if (onSubmitAnswers) {
      onSubmitAnswers(draftRef.current);
    }
    onTriggerStop();
  };

  const otherPlayers = Object.values(room.players || {}).filter(p => p.id !== playerId);

  return (
    <div className="w-full max-w-4xl mx-auto my-4 px-4 space-y-5">
      
      {/* Sticky Top Status Bar: Letter, Timer & Progress */}
      <div className="sticky top-16 z-20 bg-paper-50/95 backdrop-blur-md border-2 border-paper-border rounded-2xl p-4 shadow-notebook flex items-center justify-between gap-4">
        
        {/* Round Letter Pill */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-amber-600 text-white flex items-center justify-center font-black text-2xl sm:text-3xl shadow-sm border border-amber-700">
            {letter}
          </div>
          <div>
            <span className="text-[11px] font-bold text-ink-400 uppercase tracking-wider block">
              {t.round} {room.currentRound} {t.of} {room.settings.totalRounds}
            </span>
            <span className="text-xs sm:text-sm font-bold text-ink-800">
              {t.currentLetter}: <strong className="text-amber-700 text-base">{letter}</strong>
            </span>
          </div>
        </div>

        {/* Real-time Authoritative Countdown Timer */}
        <div className={`flex items-center gap-2 px-3.5 py-2 rounded-xl border font-mono font-black text-lg sm:text-xl transition-all ${
          timeLeft <= 10 
            ? 'bg-red-50 border-red-300 text-red-600 animate-pulse-fast shadow-tactile-red' 
            : 'bg-paper-100 border-paper-border text-ink-800'
        }`}>
          <Clock className={`w-5 h-5 ${timeLeft <= 10 ? 'text-red-500 animate-spin-fast' : 'text-amber-600'}`} />
          <span>{String(Math.floor(timeLeft / 60)).padStart(2, '0')}:{String(timeLeft % 60).padStart(2, '0')}</span>
        </div>

        {/* Personal Progress Counter */}
        <div className="hidden sm:flex flex-col items-end">
          <span className="text-[11px] font-bold text-ink-400 uppercase tracking-wider">
            {t.categoriesFilled}
          </span>
          <div className="flex items-center gap-1.5 font-bold text-sm">
            <span className={isAllFilled ? 'text-emerald-600' : 'text-amber-700'}>
              {filledCount} / {CATEGORIES_DEF.length}
            </span>
            {isAllFilled && <Sparkles className="w-4 h-4 text-emerald-500" />}
          </div>
        </div>

      </div>

      {/* Other Players Progress Pills */}
      {otherPlayers.length > 0 && (
        <div className="bg-paper-50 border border-paper-border rounded-xl px-4 py-2.5 flex items-center gap-3 overflow-x-auto text-xs">
          <span className="text-ink-400 font-bold flex items-center gap-1 shrink-0">
            <Users className="w-3.5 h-3.5 text-amber-600" />
            Lobby:
          </span>
          <div className="flex items-center gap-2 flex-wrap">
            {otherPlayers.map(p => (
              <div 
                key={p.id}
                className="bg-paper-100 border border-paper-border px-2.5 py-1 rounded-lg flex items-center gap-1.5 shrink-0"
              >
                <span className="font-semibold text-ink-800 max-w-[80px] truncate">{p.name}:</span>
                <span className={`font-mono font-bold ${p.progress === 9 ? 'text-emerald-600' : 'text-ink-500'}`}>
                  {p.progress || 0}/9
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 9 Categories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {CATEGORIES_DEF.map((cat, index) => {
          const IconComponent = ICON_MAP[cat.iconName] || Box;
          const currentVal = draft[cat.id] || '';
          const hasVal = currentVal.trim().length > 0;

          return (
            <div 
              key={cat.id}
              className={`p-3.5 rounded-2xl border transition-all ${
                hasVal 
                  ? 'bg-paper-50 border-amber-300 shadow-2xs' 
                  : 'bg-paper-50/80 border-paper-border'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <label 
                  htmlFor={`input-${cat.id}`}
                  className="text-xs font-bold text-ink-800 flex items-center gap-1.5 cursor-pointer"
                >
                  <IconComponent className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>{cat.labels[room.settings.lang] || cat.labels.ar}</span>
                </label>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                  {letter}
                </span>
              </div>

              <input
                id={`input-${cat.id}`}
                ref={el => inputRefs.current[index] = el}
                type="text"
                autoComplete="off"
                autoCorrect="off"
                spellCheck="false"
                disabled={hasStopped}
                value={currentVal}
                placeholder={cat.placeholder[room.settings.lang] || cat.placeholder.ar}
                onChange={(e) => handleInputChange(cat.id, e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, index)}
                className="w-full px-3.5 py-2 rounded-xl input-notebook text-sm font-medium text-ink-900"
              />
            </div>
          );
        })}
      </div>

      {/* STOP BUTTON TRIGGER */}
      <div className="pt-2 pb-6">
        <button
          type="button"
          onClick={handleStop}
          disabled={hasStopped}
          className={`w-full py-4 sm:py-5 rounded-2xl font-black text-lg sm:text-xl text-white shadow-tactile-red flex items-center justify-center gap-3 transition-all btn-tactile ${
            isAllFilled 
              ? 'bg-red-600 hover:bg-red-700 animate-bounce-short cursor-pointer' 
              : 'bg-red-600/90 hover:bg-red-600 cursor-pointer'
          } ${hasStopped ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <OctagonAlert className="w-6 h-6 fill-white text-red-600" />
          <span>{t.stopButton}</span>
        </button>
        <p className="text-center text-xs text-ink-500 mt-2 font-medium">
          {t.stopHint}
        </p>
      </div>

    </div>
  );
}
