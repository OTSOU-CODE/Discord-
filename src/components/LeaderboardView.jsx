import React from 'react';
import { Trophy, Medal, ArrowRight, Play, Crown, Sparkles } from 'lucide-react';
import { playClick } from '../utils/soundEffects';

export function LeaderboardView({ 
  room, 
  playerId, 
  onNextRound, 
  t 
}) {
  const isHost = room.hostId === playerId;
  const isLastRound = room.currentRound >= room.settings.totalRounds;

  // Rank players by score descending
  const rankedPlayers = Object.values(room.players || {})
    .sort((a, b) => b.score - a.score);

  const getRankBadge = (index) => {
    if (index === 0) return '🥇';
    if (index === 1) return '🥈';
    if (index === 2) return '🥉';
    return `#${index + 1}`;
  };

  return (
    <div className="w-full max-w-2xl mx-auto my-6 px-4 space-y-6">
      
      {/* Leaderboard Card */}
      <div className="bg-paper-50 border-2 border-paper-border rounded-3xl p-6 sm:p-8 shadow-notebook">
        
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-bold mb-2">
            <Trophy className="w-4 h-4 text-amber-600" />
            <span>{t.round} {room.currentRound} {t.of} {room.settings.totalRounds}</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-ink-900">
            {t.leaderboardTitle}
          </h2>
        </div>

        {/* Players Standings List */}
        <div className="space-y-3">
          {rankedPlayers.map((p, idx) => {
            const isMe = p.id === playerId;
            const rankBadge = getRankBadge(idx);
            const isTop3 = idx < 3;

            return (
              <div 
                key={p.id}
                className={`p-4 rounded-2xl border-2 flex items-center justify-between transition ${
                  isMe 
                    ? 'bg-amber-50/80 border-amber-400 shadow-2xs' 
                    : isTop3
                      ? 'bg-white border-paper-border shadow-2xs'
                      : 'bg-paper-100/60 border-paper-border'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xl sm:text-2xl font-black w-8 text-center shrink-0">
                    {rankBadge}
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm sm:text-base text-ink-900 truncate">
                        {p.name}
                      </span>
                      {p.id === room.hostId && (
                        <Crown className="w-3.5 h-3.5 text-amber-500 fill-amber-400 shrink-0" />
                      )}
                    </div>
                    {isMe && (
                      <span className="text-[10px] font-semibold text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded">
                        {t.you}
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-end shrink-0">
                  <span className="text-lg sm:text-xl font-mono font-black text-ink-900 block leading-none">
                    {p.score} <span className="text-xs font-normal text-ink-500">pts</span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Host Controls */}
        <div className="mt-8 pt-4 border-t border-paper-border">
          {isHost ? (
            <button
              onClick={() => {
                playClick();
                onNextRound();
              }}
              className="w-full py-4 bg-amber-600 hover:bg-amber-700 text-white rounded-2xl font-bold text-base shadow-tactile flex items-center justify-center gap-2 btn-tactile transition cursor-pointer"
            >
              <span>{isLastRound ? t.finalPodium : t.nextRound}</span>
              <ArrowRight className="w-5 h-5 rtl:rotate-180" />
            </button>
          ) : (
            <div className="text-center p-3 text-xs text-ink-500 font-medium animate-pulse">
              Waiting for host to start next round...
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
