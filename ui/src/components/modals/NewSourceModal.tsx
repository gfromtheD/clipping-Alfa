import React, { useState } from 'react';
import { X, Youtube, Upload, Sparkles, Cpu } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const NewSourceModal: React.FC = () => {
  const { isNewSourceOpen, closeNewSourceModal, startProcessing } = usePipelineStore();
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [language, setLanguage] = useState('auto');
  const [model, setModel] = useState('small');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isNewSourceOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl.trim()) return;

    setIsSubmitting(true);
    try {
      await startProcessing({
        youtubeUrl: youtubeUrl.trim(),
        language,
      });
      closeNewSourceModal();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg bg-[#F8F8F4] border border-[#D5D5CF] rounded-[36px] p-6 sm:p-8 shadow-2xl relative overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with Close */}
        <div className="flex items-center justify-between pb-4 border-b border-[#D5D5CF]/60 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E5F5A4] text-[#1A1A18] flex items-center justify-center font-bold">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[20px] font-bold text-[#1A1A18] leading-tight">
                New Video Source
              </h2>
              <p className="text-[12px] text-[#6B6B66]">
                Ingest from YouTube or upload local media for vertical clipping
              </p>
            </div>
          </div>

          <button
            onClick={closeNewSourceModal}
            className="w-9 h-9 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18] hover:border-[#1A1A18] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Ingest Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* YouTube URL input */}
          <div>
            <label className="block text-[13px] font-semibold text-[#1A1A18] mb-2 flex items-center gap-2">
              <Youtube className="w-4 h-4 text-red-600 fill-red-600" />
              YouTube Video URL
            </label>
            <div className="relative">
              <input
                type="url"
                placeholder="https://www.youtube.com/watch?v=..."
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                className="w-full h-12 px-4 rounded-[18px] bg-white border border-[#D5D5CF] text-[#1A1A18] text-[13px] placeholder:text-[#9E9E98] focus:outline-none focus:border-[#1A1A18] transition-all shadow-inner"
              />
            </div>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 my-2">
            <div className="flex-1 h-[1px] bg-[#D5D5CF]" />
            <span className="text-[11px] font-semibold text-[#9E9E98] uppercase tracking-wider">
              or drag & drop
            </span>
            <div className="flex-1 h-[1px] bg-[#D5D5CF]" />
          </div>

          {/* Dropzone Container */}
          <div className="w-full border-2 border-dashed border-[#D5D5CF] hover:border-[#1A1A18] rounded-[24px] p-6 text-center bg-white/50 hover:bg-white transition-all cursor-pointer group">
            <Upload className="w-8 h-8 text-[#9E9E98] group-hover:text-[#1A1A18] mx-auto mb-2 transition-colors" />
            <div className="text-[13px] font-semibold text-[#1A1A18]">
              Drop local MP4 / MOV video file here
            </div>
            <div className="text-[11px] text-[#6B6B66] mt-0.5">
              Processed locally inside input/ directory
            </div>
          </div>

          {/* Pipeline Options Grid */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div>
              <label className="block text-[11px] font-semibold text-[#6B6B66] uppercase tracking-wider mb-1.5">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full h-10 px-3 rounded-[14px] bg-white border border-[#D5D5CF] text-[12px] font-medium text-[#1A1A18] focus:outline-none focus:border-[#1A1A18]"
              >
                <option value="auto">Auto Detect</option>
                <option value="es">Spanish (es)</option>
                <option value="en">English (en)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[#6B6B66] uppercase tracking-wider mb-1.5">
                Whisper Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full h-10 px-3 rounded-[14px] bg-white border border-[#D5D5CF] text-[12px] font-medium text-[#1A1A18] focus:outline-none focus:border-[#1A1A18]"
              >
                <option value="small">Small (Fast, GPU FP16)</option>
                <option value="medium">Medium (Balanced)</option>
                <option value="large-v3">Large-v3 (Maximum Accuracy)</option>
              </select>
            </div>
          </div>

          {/* Footer Action */}
          <div className="pt-4 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] text-[#6B6B66]">
              <Cpu className="w-3.5 h-3.5 text-[#6B6B66]" />
              <span>CUDA GPU Acceleration</span>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !youtubeUrl.trim()}
              className="h-11 px-7 rounded-full bg-[#D4F63A] hover:bg-[#C4E62A] disabled:opacity-50 text-[#1A1A18] font-bold text-[13px] shadow-md hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2 cursor-pointer"
            >
              <span>{isSubmitting ? 'Iniciando...' : 'Process Video'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
