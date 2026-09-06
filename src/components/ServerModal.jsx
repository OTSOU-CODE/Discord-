import React, { useState } from 'react';
import { X, Server, CheckCircle2, AlertCircle, RefreshCw, Globe, ExternalLink, Terminal, ShieldAlert } from 'lucide-react';
import { 
  getServerUrl, 
  setServerUrl, 
  resetServerUrl, 
  testServerHealth, 
  isStaticHost,
  hasConfiguredServer 
} from '../socket';
import { playClick } from '../utils/soundEffects';

export function ServerModal({ isOpen, onClose, t, isConnected }) {
  const currentUrl = getServerUrl();
  const [inputUrl, setInputUrl] = useState(currentUrl || '');
  const [testStatus, setTestStatus] = useState(null); // null | 'testing' | { ok: boolean, message: string }

  if (!isOpen) return null;

  const handleTest = async () => {
    playClick();
    setTestStatus('testing');
    const result = await testServerHealth(inputUrl);
    if (result.ok) {
      setTestStatus({
        ok: true,
        message: t.serverConnected || 'Server is online and responding!'
      });
    } else {
      setTestStatus({
        ok: false,
        message: result.error || t.serverFailed
      });
    }
  };

  const handleSave = () => {
    playClick();
    setServerUrl(inputUrl);
  };

  const handleReset = () => {
    playClick();
    resetServerUrl();
  };

  const isGitHub = isStaticHost();

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-paper-50 border border-paper-border rounded-2xl max-w-lg w-full p-6 shadow-2xl relative animate-in fade-in zoom-in duration-200 max-h-[90vh] overflow-y-auto">
        
        {/* Close button */}
        <button
          onClick={() => {
            playClick();
            onClose();
          }}
          className="absolute top-4 end-4 p-1.5 rounded-lg text-ink-400 hover:text-ink-700 hover:bg-paper-200 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 text-amber-700 font-bold mb-1">
          <Server className="w-5 h-5" />
          <h2 className="text-lg text-ink-900">{t.serverModalTitle || 'Game Server Settings'}</h2>
        </div>
        <p className="text-xs text-ink-500 mb-4">
          {t.serverModalDesc || 'Configure the backend server URL for real-time multiplayer.'}
        </p>

        {/* GitHub Pages Informational Banner */}
        {isGitHub && !hasConfiguredServer() && (
          <div className="mb-4 bg-amber-50 border border-amber-300/80 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-amber-900">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-800 mb-0.5">
                {t.githubHostingBadge || 'Hosted on GitHub Pages'}
              </p>
              <p className="text-amber-700 leading-relaxed">
                GitHub Pages hosts the static web game. To play multiplayer, run your backend 100% natively on <strong>GitHub Codespaces</strong> (no external services or accounts needed) and paste the public link below!
              </p>
            </div>
          </div>
        )}

        {/* Current status indicator */}
        <div className="bg-paper-100 border border-paper-border rounded-xl p-3 mb-4 flex items-center justify-between text-xs">
          <div>
            <span className="text-ink-500 font-medium block text-[11px] uppercase tracking-wider">
              {t.currentServer || 'Active Server'}
            </span>
            <span className="font-mono text-ink-800 font-semibold break-all">
              {currentUrl || '(Same origin / unconfigured)'}
            </span>
          </div>
          <div className={`px-2.5 py-1 rounded-full font-medium flex items-center gap-1.5 text-xs shrink-0 ${
            isConnected 
              ? 'bg-emerald-100 text-emerald-800' 
              : 'bg-red-100 text-red-800'
          }`}>
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            {isConnected ? 'Online' : 'Offline'}
          </div>
        </div>

        {/* Server URL Input */}
        <div className="mb-4">
          <label className="block text-xs font-semibold text-ink-700 mb-1.5">
            {t.serverUrlLabel || 'GitHub Codespaces or Backend URL'}
          </label>
          <input
            type="url"
            value={inputUrl}
            onChange={(e) => {
              setInputUrl(e.target.value);
              setTestStatus(null);
            }}
            placeholder={t.serverUrlPlaceholder || 'https://<codespace>-3000.app.github.dev'}
            className="w-full text-xs font-mono bg-white border border-paper-border rounded-xl px-3 py-2.5 text-ink-900 focus:outline-hidden focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500 transition shadow-2xs"
          />
          {typeof window !== 'undefined' && window.location.protocol === 'https:' && /^http:\/\/(?!localhost|127\.0\.0\.1)/i.test(inputUrl.trim()) && (
            <p className="text-[11px] text-amber-700 mt-1.5 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 text-amber-600 shrink-0" />
              <span>GitHub Pages requires HTTPS. Unsecured HTTP URLs will be blocked by the browser.</span>
            </p>
          )}
        </div>

        {/* Test Result Message */}
        {testStatus === 'testing' && (
          <div className="mb-4 text-xs flex items-center gap-2 text-ink-600 bg-paper-200/50 p-2.5 rounded-lg font-mono">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-600" />
            <span>{t.testingConnection || 'Testing connection...'}</span>
          </div>
        )}
        {testStatus && testStatus !== 'testing' && (
          <div className={`mb-4 text-xs p-2.5 rounded-lg flex items-center gap-2 font-mono ${
            testStatus.ok 
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' 
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {testStatus.ok ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            )}
            <span className="break-all">{testStatus.message}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 mb-5">
          <button
            type="button"
            onClick={handleTest}
            disabled={!inputUrl || testStatus === 'testing'}
            className="flex-1 text-xs font-semibold px-3 py-2 rounded-lg bg-paper-200 hover:bg-paper-300 border border-paper-border text-ink-800 transition disabled:opacity-50"
          >
            {t.testAndConnect || 'Test Connection'}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!inputUrl}
            className="flex-1 text-xs font-semibold px-3 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white shadow-2xs transition disabled:opacity-50"
          >
            {t.connectServer || 'Save & Connect'}
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="text-xs font-semibold px-3 py-2 rounded-lg border border-paper-border text-ink-500 hover:text-ink-800 hover:bg-paper-200 transition"
            title={t.resetToDefault || 'Reset to Default'}
          >
            {t.resetToDefault || 'Reset'}
          </button>
        </div>

        {/* GitHub Native Hosting Guide Section */}
        <div className="border-t border-paper-border pt-4">
          <h3 className="text-xs font-bold text-ink-800 mb-2 flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5 text-amber-600" />
            {t.serverHelpTitle || '100% Native GitHub Hosting Options (Zero External Services):'}
          </h3>
          
          <div className="space-y-2.5 text-[11px] text-ink-600">
            {/* GitHub Codespaces Option */}
            <div className="bg-paper-100 p-3 rounded-xl border border-paper-border">
              <div className="font-semibold text-ink-800 mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-amber-900">
                  <Terminal className="w-3.5 h-3.5 text-amber-700" />
                  🐙 GitHub Codespaces (100% Free & Native to GitHub)
                </span>
                <span className="bg-emerald-100 text-emerald-800 text-[10px] px-1.5 py-0.5 rounded font-medium">Recommended</span>
              </div>
              <p className="text-ink-600 text-[11px] mb-2 leading-relaxed">
                Run the multiplayer backend directly in the cloud on GitHub with 60 free hours every month. Zero local setup, zero external websites or services.
              </p>
              <ol className="list-decimal list-inside space-y-1 text-[10px] text-ink-700 bg-white/60 p-2 rounded-lg border border-paper-border/60">
                <li>Go to your GitHub repository and click <strong>Code</strong> &gt; <strong>Codespaces</strong> &gt; <strong>Create codespace</strong>.</li>
                <li>GitHub launches the server automatically with public port 3000.</li>
                <li>Copy the public HTTPS link (<code>https://&lt;name&gt;-3000.app.github.dev</code>) and paste it above!</li>
              </ol>
            </div>

            {/* Local Host Option */}
            <div className="bg-paper-100 p-2.5 rounded-lg border border-paper-border">
              <div className="font-semibold text-ink-800 mb-0.5 flex items-center gap-1.5">
                <Server className="w-3 h-3 text-amber-600" />
                Local PC &amp; Wi-Fi Play:
              </div>
              <p className="text-ink-500 text-[10px] leading-relaxed">
                Run <code>npm start</code> on your machine to play locally at <code>http://localhost:3000</code> or with friends on your local Wi-Fi router.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
