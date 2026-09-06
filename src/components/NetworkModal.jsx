import React, { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { X, Copy, Check, QrCode, Globe, Wifi, Terminal } from 'lucide-react';
import { playClick } from '../utils/soundEffects';
import { getApiUrl, getServerUrl, isStaticHost, hasConfiguredServer, getInviteUrl } from '../socket';

export function NetworkModal({ isOpen, onClose, t, roomCode }) {
  const canvasRef = useRef(null);
  const [networkInfo, setNetworkInfo] = useState(null);
  const [selectedUrl, setSelectedUrl] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const webInviteUrl = getInviteUrl(roomCode);
    setSelectedUrl(webInviteUrl);

    // Only query local network IPs if running on local server (not on static host)
    if (!isStaticHost()) {
      fetch(getApiUrl('/api/network'))
        .then(r => r.json())
        .then(data => {
          setNetworkInfo(data);
          const base = data?.suggestedLocalUrl || (window.location.origin + window.location.pathname);
          const cleanBase = base.replace(/\/+$/, '');
          const localUrl = roomCode ? `${cleanBase}/?join=${roomCode}` : `${cleanBase}/`;
          setSelectedUrl(localUrl);
        })
        .catch(() => {
          setSelectedUrl(webInviteUrl);
        });
    }
  }, [isOpen, roomCode]);

  useEffect(() => {
    if (!canvasRef.current || !selectedUrl) return;

    QRCode.toCanvas(
      canvasRef.current,
      selectedUrl,
      {
        width: 180,
        margin: 1,
        color: {
          dark: '#1E293B',
          light: '#FFFFFF'
        }
      },
      (err) => {
        if (err) console.error(err);
      }
    );
  }, [selectedUrl]);

  if (!isOpen) return null;

  const copyUrl = () => {
    playClick();
    navigator.clipboard.writeText(selectedUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-paper-50 border border-paper-border rounded-2xl max-w-lg w-full p-6 shadow-2xl relative animate-in fade-in zoom-in duration-200">
        
        <button
          onClick={() => {
            playClick();
            onClose();
          }}
          className="absolute top-4 end-4 p-1.5 rounded-lg text-ink-400 hover:text-ink-700 hover:bg-paper-200 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 text-amber-700 font-bold mb-1">
          <Wifi className="w-5 h-5" />
          <h2 className="text-lg text-ink-900">{t.networkModalTitle}</h2>
        </div>
        <p className="text-xs text-ink-500 mb-5">
          {t.networkModalDesc}
        </p>

        {/* QR Code and Quick Scan */}
        <div className="flex flex-col sm:flex-row items-center gap-5 bg-paper-100 p-4 rounded-xl border border-paper-border mb-4">
          <div className="bg-white p-2 rounded-xl shadow-xs border border-paper-border shrink-0">
            <canvas ref={canvasRef} className="rounded-lg" />
          </div>
          <div className="flex-1 text-center sm:text-start">
            <span className="text-xs font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-md inline-flex items-center gap-1 mb-2">
              <QrCode className="w-3.5 h-3.5" />
              Scan on Mobile Phone
            </span>
            <p className="text-xs text-ink-600 mb-3 leading-relaxed">
              Connect your phone to the same Wi-Fi network and scan this QR code with the camera app to enter the lobby!
            </p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={selectedUrl}
                className="text-xs font-mono bg-white border border-paper-border rounded-lg px-2.5 py-1.5 w-full text-ink-800 select-all"
              />
              <button
                onClick={copyUrl}
                className="p-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition shrink-0 shadow-2xs"
                title={t.copyInviteLink}
              >
                {copied ? <Check className="w-4 h-4 text-white" /> : <Copy className="w-4 h-4 text-white" />}
              </button>
            </div>
          </div>
        </div>

        {/* Local Network IPs List */}
        {networkInfo?.localIps?.length > 0 && (
          <div className="mb-4">
            <span className="text-xs font-semibold text-ink-700 flex items-center gap-1.5 mb-2">
              <Globe className="w-3.5 h-3.5 text-amber-600" />
              Detected Wi-Fi / Local Network URLs:
            </span>
            <div className="space-y-1.5">
              {networkInfo.localIps.map(ip => {
                const url = roomCode 
                  ? `http://${ip}:${networkInfo.port}/?join=${roomCode}` 
                  : `http://${ip}:${networkInfo.port}`;
                const isSelected = selectedUrl === url;

                return (
                  <button
                    key={ip}
                    onClick={() => {
                      playClick();
                      setSelectedUrl(url);
                    }}
                    className={`w-full text-start text-xs font-mono px-3 py-2 rounded-lg border transition flex items-center justify-between ${
                      isSelected 
                        ? 'bg-amber-50 border-amber-400 text-amber-900 font-bold' 
                        : 'bg-white border-paper-border hover:bg-paper-200 text-ink-700'
                    }`}
                  >
                    <span>{url}</span>
                    {isSelected && <span className="text-[10px] bg-amber-200 text-amber-800 px-1.5 py-0.5 rounded">Active QR</span>}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Helper Note based on Hosting Environment */}
        {(networkInfo?.isCodespaces || (typeof window !== 'undefined' && (window.location.hostname.includes('.app.github.dev') || window.location.hostname.includes('.github.dev')))) ? (
          <div className="bg-emerald-50 border border-emerald-300/70 p-3.5 rounded-xl text-xs">
            <div className="flex items-center gap-1.5 text-emerald-800 font-bold mb-1">
              <Globe className="w-3.5 h-3.5 text-emerald-600" />
              <span>{t.codespacesBadge || '100% Hosted on GitHub Codespaces'}</span>
            </div>
            <p className="text-emerald-700 text-[11px] leading-relaxed">
              Your game is running live in the cloud on GitHub's native infrastructure with public port forwarding. Anyone in the world can scan this QR code or open the link to join and play instantly!
            </p>
          </div>
        ) : isStaticHost() ? (
          <div className="bg-amber-50 border border-amber-300/70 p-3.5 rounded-xl text-xs">
            <div className="flex items-center gap-1.5 text-amber-800 font-bold mb-1">
              <Globe className="w-3.5 h-3.5 text-amber-600" />
              <span>{t.githubHostingBadge || 'Hosted on GitHub Pages'}</span>
            </div>
            <p className="text-amber-700 text-[11px] leading-relaxed">
              {hasConfiguredServer() 
                ? 'Your friends can join directly from any device or browser by scanning the QR code or clicking the invite link.'
                : 'Warning: You have not configured a backend server URL yet. Open Server Settings to connect your GitHub Codespaces backend link so players can connect.'}
            </p>
          </div>
        ) : (
          <div className="bg-paper-100 text-ink-700 p-3 rounded-xl text-xs border border-paper-border">
            <div className="flex items-center gap-1.5 text-amber-800 font-semibold mb-1">
              <Wifi className="w-3.5 h-3.5 text-amber-600" />
              Local Wi-Fi &amp; Internet Play:
            </div>
            <p className="text-ink-600 text-[11px] leading-relaxed">
              Devices on the same local Wi-Fi router can scan the QR code above to join. To play with friends anywhere in the world without installing anything, launch this repo in <strong>GitHub Codespaces</strong> for an instant 100% GitHub-hosted link!
            </p>
          </div>
        )}

      </div>
    </div>
  );
}
