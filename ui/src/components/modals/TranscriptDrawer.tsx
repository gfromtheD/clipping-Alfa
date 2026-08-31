import React, { useState } from 'react';
import { X, FileText, Search } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const TranscriptDrawer: React.FC = () => {
  const { isTranscriptDrawerOpen, toggleTranscriptDrawer, state } = usePipelineStore();
  const [searchTerm, setSearchTerm] = useState('');

  if (!isTranscriptDrawerOpen) return null;

  const segments = state.transcript?.segments || [];
  const wordCount = state.metrics.words || 0;
  const detectedLanguage = state.transcript?.language || state.source?.language || 'ES';

  const filteredSegments = searchTerm
    ? segments.filter((s) => s.text.toLowerCase().includes(searchTerm.toLowerCase()))
    : segments;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-xl h-full bg-[#F8F8F4] border-l border-[#D5D5CF] p-6 sm:p-8 flex flex-col justify-between shadow-2xl animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div>
          <div className="flex items-center justify-between pb-4 border-b border-[#D5D5CF]/60 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full bg-[#E5F5A4] text-[#1A1A18] flex items-center justify-center font-bold">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-[18px] font-bold text-[#1A1A18]">Transcripción Real</h3>
                <p className="text-[11px] text-[#6B6B66]">
                  {wordCount > 0
                    ? `${wordCount} palabras sincronizadas (${detectedLanguage})`
                    : 'Transcripción generada por Faster-Whisper'}
                </p>
              </div>
            </div>

            <button
              onClick={() => toggleTranscriptDrawer(false)}
              className="w-8 h-8 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18] cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Search bar */}
          {segments.length > 0 && (
            <div className="relative mb-4">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9E9E98]" />
              <input
                type="text"
                placeholder="Buscar palabras en la transcripción..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-10 pl-10 pr-4 rounded-full bg-white border border-[#D5D5CF] text-[12px] text-[#1A1A18] focus:outline-none focus:border-[#1A1A18]"
              />
            </div>
          )}
        </div>

        {/* Scrollable Dialogue List */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-3 my-2">
          {filteredSegments.length > 0 ? (
            filteredSegments.map((item, i) => (
              <div
                key={i}
                className="p-3.5 rounded-[18px] bg-white border border-[#D5D5CF]/70 shadow-2xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold text-[#1A1A18] font-mono bg-[#EAEAE4] px-2 py-0.5 rounded-full">
                    {item.timeFormatted || `${Math.floor(item.start)}s`}
                  </span>
                  <span className="text-[10px] text-[#9E9E98] font-mono">
                    {item.start.toFixed(1)}s — {item.end.toFixed(1)}s
                  </span>
                </div>

                <p className="text-[12px] leading-relaxed text-[#3A3A36]">
                  {item.text}
                </p>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-[#6B6B66]">
              <FileText className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-[13px] font-semibold">No hay transcripción disponible</p>
              <p className="text-[11px] mt-1">Procesa un vídeo para ver la transcripción con timestamps.</p>
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="pt-3 border-t border-[#D5D5CF]/60 flex items-center justify-between text-[11px] text-[#6B6B66]">
          <span>Modelo: Faster-Whisper (CUDA)</span>
          <span className="font-semibold text-[#1A1A18]">WhisperX Timestamps</span>
        </div>
      </div>
    </div>
  );
};
