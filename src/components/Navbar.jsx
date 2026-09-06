import React, { useState } from 'react';
import { Volume2, VolumeX, Wifi, Copy, Check, LogOut, Radio, Server } from 'lucide-react';
import { isSoundEnabled, setSoundEnabled, playClick } from '../utils/soundEffects';
import { isStaticHost, hasConfiguredServer, getInviteUrl } from '../socket';

export function Navbar({ 
  room, 
  onLeaveRoom, 
  onOpenNetworkModal, 
  onOpenServerModal, 
  t, 
  isConnected 
}) {
  const [soundOn, setSoundOn] = useState(isSoundEnabled());
  const [copied, setCopied] = useState(false);

  const toggleSound = () => {
    const next = !soundOn;
    setSoundEnabled(next);
    setSoundOn(next);
    if (next) playClick();
  };

  const copyRoomCode = () => {
    if (!room?.code) return;
    playClick();
    const url = getInviteUrl(room.code);
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <header className="w-full border-b border-paper-border bg-paper-50/90 backdrop-blur sticky top-0 z-30 shadow-xs">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        
        {/* Logo and App Title */}
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-amber-100 border border-amber-300 flex items-center justify-center text-2xl shadow-xs">
            🚌
          </div>
          <div>
            <h1 className="text-lg font-bold text-ink-900 tracking-tight leading-none flex items-center gap-2">
              <span>{t.gameTitle}</span>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-700 border border-amber-500/20">
                v1.0
              </span>
            </h1>
            <p className="text-xs text-ink-500 mt-0.5 hidden sm:block">
              {t.gameSubtitle}
            </p>
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-2">
          
          {/* Connection Status Indicator */}
          <div 
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              isConnected 
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                : 'bg-red-50 text-red-700 border-red-200 animate-pulse'
            }`}
            title={isConnected ? 'Connected' : 'Reconnecting...'}
          >
            <Radio className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-500' : 'text-red-500'}`} />
            <span className="hidden md:inline">{isConnected ? 'Online' : 'Offline'}</span>
          </div>

          {/* Active Room Code Pill */}
          {room && (
            <button
              onClick={copyRoomCode}
              className="flex items-center gap-1.5 bg-paper-200 hover:bg-paper-300 border border-paper-border text-ink-800 px-3 py-1 rounded-lg text-xs font-mono font-bold transition shadow-2xs"
              title={t.copyCode}
            >
              <span className="text-ink-500 text-[10px] tracking-wider uppercase">{t.roomCode}:</span>
              <span className="text-amber-700 text-sm tracking-widest">{room.code}</span>
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-ink-400" />}
            </button>
          )}

          {/* Server Settings Modal Button */}
          <button
            onClick={() => {
              playClick();
              onOpenServerModal?.();
            }}
            className={`p-2 rounded-lg border transition relative ${
              isStaticHost() && !hasConfiguredServer()
                ? 'bg-amber-100 hover:bg-amber-200 border-amber-300 text-amber-800 animate-pulse'
                : 'bg-paper-100 hover:bg-paper-200 border-paper-border text-ink-700'
            }`}
            title={t.serverSettings || 'Server Settings'}
          >
            <Server className="w-4 h-4" />
            {isStaticHost() && !hasConfiguredServer() && (
              <span className="absolute -top-1 -end-1 w-2.5 h-2.5 bg-amber-500 rounded-full border-2 border-white" />
            )}
          </button>

          {/* Network & QR Code Modal Button */}
          <button
            onClick={() => {
              playClick();
              onOpenNetworkModal();
            }}
            className="p-2 rounded-lg bg-paper-100 hover:bg-paper-200 border border-paper-border text-ink-700 transition"
            title={t.shareWifi}
          >
            <Wifi className="w-4 h-4" />
          </button>

          {/* Sound Toggle */}
          <button
            onClick={toggleSound}
            className="p-2 rounded-lg bg-paper-100 hover:bg-paper-200 border border-paper-border text-ink-700 transition"
            title={soundOn ? t.soundOn : t.soundOff}
          >
            {soundOn ? <Volume2 className="w-4 h-4 text-amber-700" /> : <VolumeX className="w-4 h-4 text-ink-400" />}
          </button>

          {/* Leave Room Button */}
          {room && (
            <button
              onClick={() => {
                playClick();
                onLeaveRoom();
              }}
              className="p-2 rounded-lg bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 transition"
              title={t.leaveRoom}
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}

        </div>
      </div>
    </header>
  );
}
