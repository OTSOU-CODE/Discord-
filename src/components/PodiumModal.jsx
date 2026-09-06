import React, { useEffect } from 'react';
import confetti from 'canvas-confetti';
import { Trophy, Crown, RotateCcw, Sparkles } from 'lucide-react';
import { playVictoryFanfare, playClick } from '../utils/soundEffects';

export function PodiumModal({ room, playerId, onRestartGame, t }) {
  const isHost = room.hostId === playerId;
  const rankedPlayers = Object.values(room.players || {}).sort((a, b) => b.score - a.score);

  const firstPlace = rankedPlayers[0];
  const secondPlace = rankedPlayers[1];
  const thirdPlace = rankedPlayers[2];

  useEffect(() => {
    // Play fanfare
    playVictoryFanfare();

    // Canvas confetti burst
    const count = 200;
    const defaults = {
      origin: { y: 0.7 }
    };

    function fire(particleRatio, opts) {
      confetti({
        ...defaults,
        ...opts,
        particleCount: Math.floor(count * particleRatio)
      });
    }

    fire(0.25, {
      spread: 26,
      startVelocity: 55,
    });
    fire(0.2, {
      spread: 60,
    });
    fire(0.35, {
      spread: 100,
      decay: 0.91,
      scalar: 0.8
    });
    fire(0.1, {
      spread: 120,
      startVelocity: 25,
      decay: 0.92,
      scalar: 1.2
    });
    fire(0.1, {
      spread: 120,
      startVelocity: 45,
    });
  }, []);

  return (
    <div className="w-full max-w-2xl mx-auto my-6 px-4 space-y-6">
      
      <div className="bg-paper-50 border-2 border-paper-border rounded-3xl p-6 sm:p-8 shadow-notebook text-center relative overflow-hidden">
        
        <div className="inline-flex items-center gap-2 px-4 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-black uppercase tracking-wider mb-3">
          <Sparkles className="w-4 h-4 text-amber-600" />
          <span>{t.finalPodium}</span>
        </div>

        <h2 className="text-3xl sm:text-4xl font-black text-ink-900 mb-2">
          {firstPlace?.name} 🏆
        </h2>
        <p className="text-sm font-semibold text-amber-700 mb-8">
          {t.winner}
        </p>

        {/* Podium Columns */}
        <div className="flex items-end justify-center gap-3 sm:gap-4 max-w-md mx-auto my-8 h-64">
          
          {/* 2nd Place */}
          {secondPlace && (
            <div className="flex-1 flex flex-col items-center">
              <div className="text-xs font-bold text-ink-800 truncate max-w-[80px] mb-1">
                {secondPlace.name}
              </div>
              <span className="text-xs font-mono font-bold text-ink-500 mb-1">
                {secondPlace.score} pts
              </span>
              <div className="w-full h-36 rounded-t-2xl bg-slate-200 border-2 border-slate-300 flex flex-col items-center justify-center p-2 shadow-sm">
                <span className="text-3xl">🥈</span>
                <span className="text-xs font-bold text-slate-700 mt-1">2nd</span>
              </div>
            </div>
          )}

          {/* 1st Place (Tallest) */}
          {firstPlace && (
            <div className="flex-1 flex flex-col items-center">
              <Crown className="w-7 h-7 text-amber-500 fill-amber-400 mb-1 animate-bounce" />
              <div className="text-sm font-black text-amber-900 truncate max-w-[90px] mb-1">
                {firstPlace.name}
              </div>
              <span className="text-xs font-mono font-bold text-amber-700 mb-1">
                {firstPlace.score} pts
              </span>
              <div className="w-full h-48 rounded-t-2xl bg-amber-200 border-2 border-amber-400 flex flex-col items-center justify-center p-2 shadow-md">
                <span className="text-4xl">🥇</span>
                <span className="text-xs font-black text-amber-900 mt-1">1st</span>
              </div>
            </div>
          )}

          {/* 3rd Place */}
          {thirdPlace && (
            <div className="flex-1 flex flex-col items-center">
              <div className="text-xs font-bold text-ink-800 truncate max-w-[80px] mb-1">
                {thirdPlace.name}
              </div>
              <span className="text-xs font-mono font-bold text-ink-500 mb-1">
                {thirdPlace.score} pts
              </span>
              <div className="w-full h-28 rounded-t-2xl bg-amber-100 border-2 border-amber-300 flex flex-col items-center justify-center p-2 shadow-xs">
                <span className="text-3xl">🥉</span>
                <span className="text-xs font-bold text-amber-800 mt-1">3rd</span>
              </div>
            </div>
          )}

        </div>

        {/* Host Restart Controls */}
        <div className="mt-8 pt-4 border-t border-paper-border">
          {isHost ? (
            <button
              onClick={() => {
                playClick();
                onRestartGame();
              }}
              className="w-full py-4 bg-amber-600 hover:bg-amber-700 text-white rounded-2xl font-bold text-base shadow-tactile flex items-center justify-center gap-2 btn-tactile transition cursor-pointer"
            >
              <RotateCcw className="w-5 h-5" />
              <span>{t.playAgain}</span>
            </button>
          ) : (
            <div className="text-center p-3 text-xs text-ink-500 font-medium animate-pulse">
              Waiting for host to restart game...
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
