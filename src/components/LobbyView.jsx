import React, { useState } from 'react';
import { 
  Crown, 
  Users, 
  Play, 
  Copy, 
  Check, 
  Wifi, 
  UserMinus, 
  Settings, 
  Clock, 
  Globe2, 
  Layers, 
  Sparkles,
  Share2,
  QrCode
} from 'lucide-react';
import { playClick } from '../utils/soundEffects';
import { getInviteUrl } from '../socket';

export function LobbyView({ 
  room, 
  playerId, 
  onStartGame, 
  onKickPlayer, 
  onUpdateSettings, 
  onOpenNetworkModal, 
  t 
}) {
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const isHost = room?.hostId === playerId;
  const players = Object.values(room?.players || {});

  const copyRoomCode = () => {
    playClick();
    navigator.clipboard.writeText(room.code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const copyInviteLink = () => {
    playClick();
    const url = getInviteUrl(room.code);
    navigator.clipboard.writeText(url);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className="w-full max-w-3xl mx-auto my-6 px-4 space-y-6">
      
      {/* Top Banner: Room Code & Quick Share */}
      <div className="bg-paper-50 border-2 border-paper-border rounded-3xl p-6 shadow-notebook flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-start">
        <div>
          <span className="text-xs font-bold text-ink-400 uppercase tracking-wider block mb-1">
            {t.roomCode}
          </span>
          <div className="flex items-center gap-3 justify-center sm:justify-start">
            <span className="text-4xl sm:text-5xl font-mono font-black text-amber-700 tracking-widest">
              {room.code}
            </span>
            <button
              onClick={copyRoomCode}
              className="p-2.5 rounded-xl bg-paper-200 hover:bg-paper-300 border border-paper-border text-ink-700 transition shadow-2xs"
              title={t.copyCode}
            >
              {copiedCode ? <Check className="w-5 h-5 text-emerald-600" /> : <Copy className="w-5 h-5" />}
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center sm:justify-end gap-2.5">
          {/* Prominent Direct Copy Invite Link */}
          <button
            onClick={copyInviteLink}
            className="px-4 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold flex items-center gap-2 transition shadow-tactile btn-tactile"
            title={t.copyInviteLink}
          >
            {copiedLink ? <Check className="w-4 h-4 text-white" /> : <Share2 className="w-4 h-4 text-white" />}
            <span>{copiedLink ? t.linkCopied : t.inviteFriends}</span>
          </button>

          <button
            onClick={() => {
              playClick();
              onOpenNetworkModal();
            }}
            className="px-4 py-2.5 rounded-xl bg-paper-100 hover:bg-paper-200 border border-paper-border text-ink-800 text-xs font-bold flex items-center gap-2 transition shadow-2xs"
            title={t.shareWifi}
          >
            <QrCode className="w-4 h-4 text-amber-600" />
            <span>{t.shareWifi}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Players List & Settings */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Players List (2 columns wide on md) */}
        <div className="md:col-span-2 bg-paper-50 border-2 border-paper-border rounded-3xl p-6 shadow-notebook">
          <div className="flex items-center justify-between mb-4 border-b border-paper-border pb-3">
            <h2 className="text-sm font-bold text-ink-800 flex items-center gap-2">
              <Users className="w-4 h-4 text-amber-600" />
              <span>{t.playersInLobby}</span>
            </h2>
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-300">
              {players.length} {players.length === 1 ? 'Player' : 'Players'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {players.map((p) => {
              const isCurrentPlayer = p.id === playerId;
              const isPlayerHost = p.id === room.hostId;

              return (
                <div
                  key={p.id}
                  className={`p-3 rounded-2xl border flex items-center justify-between transition ${
                    isCurrentPlayer
                      ? 'bg-amber-50/70 border-amber-300 shadow-2xs'
                      : 'bg-white border-paper-border'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-xl bg-paper-200 border border-paper-border flex items-center justify-center font-bold text-ink-800 text-sm shrink-0">
                      {p.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-bold text-ink-900 truncate">
                          {p.name}
                        </span>
                        {isPlayerHost && (
                          <Crown className="w-3.5 h-3.5 text-amber-500 fill-amber-400 shrink-0" title={t.host} />
                        )}
                      </div>
                      {isCurrentPlayer && (
                        <span className="text-[10px] font-semibold text-amber-700 bg-amber-100/80 px-1.5 py-0.2 rounded">
                          {t.you}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Kick Button (Visible only to Host, cannot kick self) */}
                  {isHost && !isPlayerHost && (
                    <button
                      onClick={() => {
                        playClick();
                        onKickPlayer(p.id);
                      }}
                      className="p-1.5 text-ink-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                      title={t.kick}
                    >
                      <UserMinus className="w-4 h-4" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {/* Host Start Button OR Non-host Waiting Notice */}
          <div className="mt-8 pt-4 border-t border-paper-border">
            {isHost ? (
              <button
                onClick={() => {
                  playClick();
                  onStartGame();
                }}
                className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold text-base shadow-tactile-green flex items-center justify-center gap-2.5 btn-tactile transition cursor-pointer"
              >
                <Play className="w-5 h-5 fill-current" />
                <span>{t.startGame}</span>
              </button>
            ) : (
              <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200 text-center text-ink-700 text-sm font-medium flex items-center justify-center gap-2.5 animate-pulse">
                <Sparkles className="w-4 h-4 text-amber-600" />
                <span>{t.waitingForHost}</span>
              </div>
            )}
          </div>
        </div>

        {/* Room Settings Summary & Host Controls (1 column) */}
        <div className="bg-paper-50 border-2 border-paper-border rounded-3xl p-6 shadow-notebook space-y-4">
          <h2 className="text-sm font-bold text-ink-800 flex items-center gap-2 border-b border-paper-border pb-3">
            <Settings className="w-4 h-4 text-amber-600" />
            <span>{t.settings}</span>
          </h2>

          <div className="space-y-3 text-xs">
            {/* Language */}
            <div className="bg-white p-3 rounded-xl border border-paper-border flex items-center justify-between">
              <span className="text-ink-500 flex items-center gap-1.5 font-medium">
                <Globe2 className="w-3.5 h-3.5 text-amber-600" />
                {t.selectLanguage}
              </span>
              <span className="font-bold text-ink-900 uppercase">
                {room.settings?.lang === 'ar' ? 'العربية' : room.settings?.lang === 'en' ? 'English' : 'Français'}
              </span>
            </div>

            {/* Round Duration */}
            <div className="bg-white p-3 rounded-xl border border-paper-border flex items-center justify-between">
              <span className="text-ink-500 flex items-center gap-1.5 font-medium">
                <Clock className="w-3.5 h-3.5 text-amber-600" />
                {t.roundDuration}
              </span>
              <span className="font-bold text-ink-900">
                {room.settings?.roundDuration} {t.seconds}
              </span>
            </div>

            {/* Total Rounds */}
            <div className="bg-white p-3 rounded-xl border border-paper-border flex items-center justify-between">
              <span className="text-ink-500 flex items-center gap-1.5 font-medium">
                <Layers className="w-3.5 h-3.5 text-amber-600" />
                {t.totalRounds}
              </span>
              <span className="font-bold text-ink-900">
                {room.settings?.totalRounds} {t.rounds}
              </span>
            </div>

            {/* Rare Letters Toggle Indicator */}
            <div className="bg-white p-3 rounded-xl border border-paper-border flex items-center justify-between">
              <span className="text-ink-500 font-medium">
                {t.includeRareLetters}
              </span>
              <span className={`font-bold ${room.settings?.includeRare ? 'text-emerald-600' : 'text-ink-400'}`}>
                {room.settings?.includeRare ? 'ON' : 'OFF'}
              </span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
