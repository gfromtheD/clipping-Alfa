import React, { useState } from 'react';
import { X, Settings as SettingsIcon, Sliders, Cpu, Save } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const SettingsModal: React.FC = () => {
  const { isSettingsOpen, toggleSettingsModal, state } = usePipelineStore();
  const [model, setModel] = useState(state.config.model);
  const [device, setDevice] = useState(state.config.device);
  const [minDuration, setMinDuration] = useState(state.config.minDuration);
  const [maxDuration, setMaxDuration] = useState(state.config.maxDuration);
  const [maxClips, setMaxClips] = useState(state.config.maxClips);
  const [subtitleMargin, setSubtitleMargin] = useState(state.config.subtitleMarginRatio);

  if (!isSettingsOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg bg-[#F8F8F4] border border-[#D5D5CF] rounded-[36px] p-6 sm:p-8 shadow-2xl relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-4 border-b border-[#D5D5CF]/60 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E5F5A4] text-[#1A1A18] flex items-center justify-center">
              <SettingsIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[20px] font-bold text-[#1A1A18]">Pipeline Settings</h2>
              <p className="text-[12px] text-[#6B6B66]">Global AI parameters & video encoding options</p>
            </div>
          </div>

          <button
            onClick={() => toggleSettingsModal(false)}
            className="w-9 h-9 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-semibold text-[#6B6B66] uppercase tracking-wider mb-1.5 flex items-center gap-1">
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
              <label className="block text-[11px] font-semibold text-[#6B6B66] uppercase tracking-wider mb-1.5 flex items-center gap-1">
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

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-[#6B6B66] mb-1">Min Duration (s)</label>
              <input
                type="number"
                value={minDuration}
                onChange={(e) => setMinDuration(Number(e.target.value))}
                className="w-full h-10 px-3 rounded-[14px] bg-white border border-[#D5D5CF] text-[12px] text-[#1A1A18]"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-[#6B6B66] mb-1">Max Duration (s)</label>
              <input
                type="number"
                value={maxDuration}
                onChange={(e) => setMaxDuration(Number(e.target.value))}
                className="w-full h-10 px-3 rounded-[14px] bg-white border border-[#D5D5CF] text-[12px] text-[#1A1A18]"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-[#6B6B66] mb-1">Max Clips</label>
              <input
                type="number"
                value={maxClips}
                onChange={(e) => setMaxClips(Number(e.target.value))}
                className="w-full h-10 px-3 rounded-[14px] bg-white border border-[#D5D5CF] text-[12px] text-[#1A1A18]"
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

        <div className="pt-6 flex justify-end">
          <button
            onClick={() => toggleSettingsModal(false)}
            className="h-11 px-6 rounded-full bg-[#D4F63A] hover:bg-[#C4E62A] text-[#1A1A18] font-bold text-[13px] shadow-md flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            <span>Save Configuration</span>
          </button>
        </div>
      </div>
    </div>
  );
};
