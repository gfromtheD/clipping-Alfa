import React, { useState } from 'react';
import { X, Settings as SettingsIcon, Sliders, Cpu, Save, Globe, Key, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const SettingsModal: React.FC = () => {
  const {
    isSettingsOpen,
    toggleSettingsModal,
    state,
    apiBaseUrl,
    setApiBaseUrl,
    apiToken,
    setApiToken,
    checkBackendHealth,
    backendHealth,
    isConnected,
  } = usePipelineStore();

  const [model, setModel] = useState(state.config.model);
  const [device, setDevice] = useState(state.config.device);
  const [minDuration, setMinDuration] = useState(state.config.minDuration);
  const [maxDuration, setMaxDuration] = useState(state.config.maxDuration);
  const [maxClips, setMaxClips] = useState(state.config.maxClips);
  const [subtitleMargin, setSubtitleMargin] = useState(state.config.subtitleMarginRatio);

  const [inputUrl, setInputUrl] = useState(apiBaseUrl);
  const [inputToken, setInputToken] = useState(apiToken);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);

  if (!isSettingsOpen) return null;

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    setApiBaseUrl(inputUrl);
    setApiToken(inputToken);

    const ok = await checkBackendHealth();
    setIsTesting(false);
    setTestResult(ok ? 'success' : 'error');
  };

  const handleSave = () => {
    setApiBaseUrl(inputUrl);
    setApiToken(inputToken);
    toggleSettingsModal(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-xl bg-[#F8F8F4] border border-[#D5D5CF] rounded-[36px] p-6 sm:p-8 shadow-2xl relative max-h-[92vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-4 border-b border-[#D5D5CF]/60 mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E5F5A4] text-[#1A1A18] flex items-center justify-center">
              <SettingsIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[20px] font-bold text-[#1A1A18]">Pipeline & Remote Connection</h2>
              <p className="text-[12px] text-[#6B6B66]">Conexión con el backend GPU local vía Cloudflare Tunnel</p>
            </div>
          </div>

          <button
            onClick={() => toggleSettingsModal(false)}
            className="w-9 h-9 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-5">
          {/* Section 1: Remote Backend & Tunnel Config */}
          <div className="bg-white border border-[#D5D5CF] rounded-[24px] p-4 space-y-3.5 shadow-2xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-[#1A1A18]" />
                <span className="text-[13px] font-bold text-[#1A1A18]">Backend URL (Cloudflare Tunnel)</span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] font-semibold">
                {isConnected ? (
                  <span className="text-[#84A90A] flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Conectado (GPU)
                  </span>
                ) : (
                  <span className="text-[#9E9E98] flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" /> Modo Demo
                  </span>
                )}
              </div>
            </div>

            <div>
              <input
                type="url"
                placeholder="https://tu-tunel.trycloudflare.com o https://api.tudominio.com"
                value={inputUrl}
                onChange={(e) => setInputUrl(e.target.value)}
                className="w-full h-10 px-3.5 rounded-[14px] bg-[#F8F8F4] border border-[#D5D5CF] text-[12px] text-[#1A1A18] placeholder:text-[#9E9E98] focus:outline-none focus:border-[#1A1A18]"
              />
              <p className="text-[10px] text-[#6B6B66] mt-1">
                Deja en blanco para desarrollo local (`http://localhost:8000`).
              </p>
            </div>

            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Key className="w-3.5 h-3.5 text-[#6B6B66]" />
                <label className="text-[11px] font-semibold text-[#1A1A18]">API Secret Token (CLIPPING_API_TOKEN)</label>
              </div>
              <input
                type="password"
                placeholder="Token secreto definido en tu archivo .env local"
                value={inputToken}
                onChange={(e) => setInputToken(e.target.value)}
                className="w-full h-10 px-3.5 rounded-[14px] bg-[#F8F8F4] border border-[#D5D5CF] text-[12px] font-mono text-[#1A1A18] placeholder:text-[#9E9E98] focus:outline-none focus:border-[#1A1A18]"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={isTesting}
                className="h-9 px-4 rounded-full bg-[#EAEAE4] hover:bg-[#DCDCD4] text-[#1A1A18] text-[11px] font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-3 h-3 ${isTesting ? 'animate-spin' : ''}`} />
                <span>{isTesting ? 'Comprobando...' : 'Probar Conexión'}</span>
              </button>

              {testResult === 'success' && (
                <span className="text-[11px] font-semibold text-[#84A90A] flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Backend activo {backendHealth?.gpu_name ? `(${backendHealth.gpu_name})` : ''}
                </span>
              )}
              {testResult === 'error' && (
                <span className="text-[11px] font-semibold text-red-500 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" /> No se pudo conectar al endpoint /health
                </span>
              )}
            </div>
          </div>

          {/* Section 2: Pipeline Parameters */}
          <div className="space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-[#6B6B66] uppercase tracking-wider mb-1 flex items-center gap-1">
                  <Cpu className="w-3 h-3" /> Compute Device
                </label>
                <select
                  value={device}
                  onChange={(e) => setDevice(e.target.value)}
                  className="w-full h-10 px-3 rounded-[14px] bg-white border border-[#D5D5CF] text-[12px] font-medium text-[#1A1A18]"
                >
                  <option value="cuda">CUDA GPU (Accelerated)</option>
                  <option value="cpu">CPU (Fallback)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#6B6B66] uppercase tracking-wider mb-1 flex items-center gap-1">
                  <Sliders className="w-3 h-3" /> Whisper Model
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full h-10 px-3 rounded-[14px] bg-white border border-[#D5D5CF] text-[12px] font-medium text-[#1A1A18]"
                >
                  <option value="small">small (Fastest)</option>
                  <option value="medium">medium (Balanced)</option>
                  <option value="large-v3">large-v3 (Maximum Accuracy)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2.5">
              <div>
                <label className="block text-[10px] font-semibold text-[#6B6B66] mb-1">Min Duration (s)</label>
                <input
                  type="number"
                  value={minDuration}
                  onChange={(e) => setMinDuration(Number(e.target.value))}
                  className="w-full h-9 px-2.5 rounded-[12px] bg-white border border-[#D5D5CF] text-[12px] text-[#1A1A18]"
                />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#6B6B66] mb-1">Max Duration (s)</label>
                <input
                  type="number"
                  value={maxDuration}
                  onChange={(e) => setMaxDuration(Number(e.target.value))}
                  className="w-full h-9 px-2.5 rounded-[12px] bg-white border border-[#D5D5CF] text-[12px] text-[#1A1A18]"
                />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#6B6B66] mb-1">Max Clips</label>
                <input
                  type="number"
                  value={maxClips}
                  onChange={(e) => setMaxClips(Number(e.target.value))}
                  className="w-full h-9 px-2.5 rounded-[12px] bg-white border border-[#D5D5CF] text-[12px] text-[#1A1A18]"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-semibold text-[#6B6B66]">Subtitle Bottom Margin Ratio</label>
                <span className="text-[11px] font-bold text-[#1A1A18]">{subtitleMargin}</span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.45"
                step="0.01"
                value={subtitleMargin}
                onChange={(e) => setSubtitleMargin(Number(e.target.value))}
                className="w-full accent-[#D4F63A]"
              />
            </div>
          </div>
        </div>

        <div className="pt-5 border-t border-[#D5D5CF]/60 flex justify-end gap-2 mt-5">
          <button
            onClick={() => toggleSettingsModal(false)}
            className="h-10 px-4 rounded-full bg-white border border-[#D5D5CF] text-[#6B6B66] hover:text-[#1A1A18] text-[12px] font-semibold"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            className="h-10 px-6 rounded-full bg-[#D4F63A] hover:bg-[#C4E62A] text-[#1A1A18] font-bold text-[12px] shadow-md flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            <span>Guardar Configuración</span>
          </button>
        </div>
      </div>
    </div>
  );
};
