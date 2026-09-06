import React from 'react';
import { 
  Check, 
  X, 
  ThumbsUp, 
  ThumbsDown, 
  ChevronLeft, 
  ChevronRight, 
  Sparkles, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  CopyCheck,
  Award,
  Crown
} from 'lucide-react';
import { CATEGORIES_DEF } from '../constants/categories';
import { playVoteSound, playClick } from '../utils/soundEffects';

export function VotingReviewView({ 
  room, 
  playerId, 
  onCastVote, 
  onChangeCategory, 
  onFinishReview, 
  t 
}) {
  const isHost = room.hostId === playerId;
  const review = room.review || {};
  const currentCategoryIndex = review.categoryIndex || 0;
  const activeCategory = CATEGORIES_DEF[currentCategoryIndex] || CATEGORIES_DEF[0];
  const catId = activeCategory.id;

  const currentRoundLetter = room.currentLetter;
  const results = review.results?.categoryResults?.[catId] || {};
  const playerStatuses = results.playerStatuses || {};

  const players = Object.values(room.players || {});

  const handleVote = (targetPlayerId, vote) => {
    playVoteSound(vote);
    onCastVote({
      categoryId: catId,
      targetPlayerId,
      vote
    });
  };

  const handlePrev = () => {
    if (currentCategoryIndex > 0) {
      playClick();
      onChangeCategory(currentCategoryIndex - 1);
    }
  };

  const handleNext = () => {
    if (currentCategoryIndex < CATEGORIES_DEF.length - 1) {
      playClick();
      onChangeCategory(currentCategoryIndex + 1);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto my-4 px-4 space-y-5">
      
      {/* Review Header Banner */}
      <div className="bg-paper-50 border-2 border-paper-border rounded-3xl p-5 shadow-notebook text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-bold mb-2">
          <Sparkles className="w-3.5 h-3.5" />
          <span>{t.reviewTitle}</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-black text-ink-900 mb-1">
          {t.votingFor}: <span className="text-amber-700 underline decoration-amber-300">{activeCategory.labels[room.settings.lang] || activeCategory.labels.ar}</span>
        </h2>
        <p className="text-xs text-ink-500">
          {t.reviewSubtitle}
        </p>

        {/* Categories Progress Tabs */}
        <div className="flex items-center justify-center gap-1.5 mt-4 overflow-x-auto py-1">
          {CATEGORIES_DEF.map((c, idx) => {
            const isActive = idx === currentCategoryIndex;
            return (
              <button
                key={c.id}
                onClick={() => {
                  playClick();
                  onChangeCategory(idx);
                }}
                className={`px-3 py-1 rounded-xl text-xs font-bold transition shrink-0 border ${
                  isActive 
                    ? 'bg-amber-600 text-white border-amber-700 shadow-xs' 
                    : 'bg-white text-ink-600 border-paper-border hover:bg-paper-100'
                }`}
              >
                {idx + 1}. {c.labels[room.settings.lang] || c.labels.ar}
              </button>
            );
          })}
        </div>
      </div>

      {/* Players Answers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {players.map((p) => {
          const status = playerStatuses[p.id] || {};
          const rawAnswer = status.rawAnswer || '';
          const hasAnswer = Boolean(rawAnswer);
          const voteKey = `${catId}:${p.id}`;
          const currentVotes = review.votes?.[voteKey] || {};
          const myVote = currentVotes[playerId];

          const approves = Object.values(currentVotes).filter(v => v === true).length;
          const rejects = Object.values(currentVotes).filter(v => v === false).length;

          // Badging logic
          let badgeText = t.autoValid;
          let badgeClass = 'bg-emerald-100 text-emerald-800 border-emerald-300';

          if (!hasAnswer) {
            badgeText = t.autoBlank;
            badgeClass = 'bg-gray-100 text-gray-600 border-gray-300';
          } else if (status.reason === 'rejected_by_vote') {
            badgeText = t.rejectedByVote;
            badgeClass = 'bg-red-100 text-red-800 border-red-300';
          } else if (status.reason === 'approved_by_vote') {
            badgeText = t.approvedByVote;
            badgeClass = 'bg-emerald-100 text-emerald-800 border-emerald-300';
          } else if (!status.startsLetter) {
            badgeText = t.autoWrongLetter;
            badgeClass = 'bg-red-100 text-red-800 border-red-300';
          } else if (status.pointReason === 'solo_valid') {
            badgeText = t.autoSolo;
            badgeClass = 'bg-amber-100 text-amber-900 border-amber-400 font-black';
          } else if (status.pointReason === 'shared') {
            badgeText = t.autoDuplicate;
            badgeClass = 'bg-blue-100 text-blue-800 border-blue-300';
          } else if (status.pointReason === 'unique') {
            badgeText = t.autoUnique;
            badgeClass = 'bg-emerald-100 text-emerald-800 border-emerald-300';
          }

          return (
            <div 
              key={p.id}
              className={`p-4 rounded-2xl border-2 transition relative ${
                status.isValid 
                  ? 'bg-paper-50 border-paper-border' 
                  : 'bg-paper-100/60 border-paper-border opacity-85'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-paper-200 border border-paper-border flex items-center justify-center font-bold text-xs text-ink-800">
                    {p.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="font-bold text-sm text-ink-900">
                    {p.name}
                  </span>
                  {p.id === room.hostId && (
                    <Crown className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
                  )}
                </div>

                {/* Score Pill */}
                <div className="flex items-center gap-1.5">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border ${badgeClass}`}>
                    +{status.points || 0} pts
                  </span>
                </div>
              </div>

              {/* The Player's Answer */}
              <div className="bg-white border border-paper-border rounded-xl p-3 my-2 shadow-inner flex items-center justify-between">
                <span className={`text-base font-bold ${
                  hasAnswer ? 'text-ink-900' : 'text-ink-400 italic text-sm'
                }`}>
                  {hasAnswer ? rawAnswer : `(${t.autoBlank})`}
                </span>

                {/* Quick Auto-check status badge */}
                <span className={`text-[11px] px-2 py-0.5 rounded-md border font-semibold ${badgeClass}`}>
                  {badgeText}
                </span>
              </div>

              {/* Peer Voting Buttons (Only if player submitted something) */}
              {hasAnswer && (
                <div className="flex items-center justify-between pt-1 border-t border-paper-border text-xs">
                  <span className="text-ink-500 font-medium">
                    Peer Vote:
                  </span>
                  {p.id === playerId ? (
                    <span className="text-[11px] font-semibold text-amber-800 bg-amber-100/70 px-2 py-0.5 rounded-md border border-amber-200">
                      {t.you}
                    </span>
                  ) : (
                    <div className="flex items-center gap-2">
                      {/* Approve Button */}
                      <button
                        onClick={() => handleVote(p.id, true)}
                        className={`px-3 py-1.5 rounded-lg border font-bold flex items-center gap-1.5 transition cursor-pointer ${
                          myVote === true
                            ? 'bg-emerald-600 text-white border-emerald-700 shadow-2xs'
                            : 'bg-white text-emerald-700 border-paper-border hover:bg-emerald-50'
                        }`}
                        title={t.voteApprove}
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span>{approves}</span>
                      </button>

                      {/* Reject Button */}
                      <button
                        onClick={() => handleVote(p.id, false)}
                        className={`px-3 py-1.5 rounded-lg border font-bold flex items-center gap-1.5 transition cursor-pointer ${
                          myVote === false
                            ? 'bg-red-600 text-white border-red-700 shadow-2xs'
                            : 'bg-white text-red-700 border-paper-border hover:bg-red-50'
                        }`}
                        title={t.voteReject}
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                        <span>{rejects}</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Navigation & Finalize Bar */}
      <div className="bg-paper-50 border-2 border-paper-border rounded-2xl p-4 shadow-notebook flex flex-col sm:flex-row items-center justify-between gap-3">
        
        {/* Prev / Next Category controls */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={handlePrev}
            disabled={currentCategoryIndex === 0}
            className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl border border-paper-border bg-white hover:bg-paper-100 disabled:opacity-40 text-xs font-bold text-ink-700 flex items-center justify-center gap-1.5 transition cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4 rtl:rotate-180" />
            <span>{t.prevCategory}</span>
          </button>
          <button
            onClick={handleNext}
            disabled={currentCategoryIndex === CATEGORIES_DEF.length - 1}
            className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl border border-paper-border bg-white hover:bg-paper-100 disabled:opacity-40 text-xs font-bold text-ink-700 flex items-center justify-center gap-1.5 transition cursor-pointer"
          >
            <span>{t.nextCategory}</span>
            <ChevronRight className="w-4 h-4 rtl:rotate-180" />
          </button>
        </div>

        {/* Host Finalize / Advance Button */}
        {isHost ? (
          <button
            onClick={() => {
              playClick();
              if (currentCategoryIndex < CATEGORIES_DEF.length - 1) {
                onChangeCategory(currentCategoryIndex + 1);
              } else {
                onFinishReview();
              }
            }}
            className="w-full sm:w-auto px-6 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs sm:text-sm font-bold shadow-tactile flex items-center justify-center gap-2 btn-tactile transition cursor-pointer"
          >
            <Award className="w-4 h-4" />
            <span>
              {currentCategoryIndex < CATEGORIES_DEF.length - 1 ? t.nextCategory : t.finishReview}
            </span>
          </button>
        ) : (
          <span className="text-xs text-ink-500 italic">
            Waiting for host to finalize review...
          </span>
        )}

      </div>

    </div>
  );
}
