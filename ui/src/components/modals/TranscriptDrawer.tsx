import React from 'react';
import { X, FileText, Search, Play } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const TranscriptDrawer: React.FC = () => {
  const { isTranscriptDrawerOpen, toggleTranscriptDrawer, openVideoPlayer } = usePipelineStore();

  if (!isTranscriptDrawerOpen) return null;

  const sampleTranscript = [
    {
      time: '00:00:05',
      speaker: 'Speaker 1',
      text: 'Welcome everyone to today’s discussion on generative media pipelines and vertical content creation.',
      highlight: false,
    },
    {
      time: '00:14:22',
      speaker: 'Speaker 1',
      text: 'The big change is not the technology, but how we think about storytelling in automated distribution.',
      highlight: true,
      clipType: 'HOOK',
    },
    {
      time: '00:14:38',
      speaker: 'Speaker 2',
      text: 'Exactly, because when you have high phonetic alignment with WhisperX, every subtitle aligns with the voice tone.',
      highlight: true,
      clipType: 'HOOK',
    },
    {
      time: '00:31:08',
      speaker: 'Speaker 1',
      text: 'How AI is changing the creative process without replacing human intuition is the cornerstone of modern tools.',
      highlight: true,
      clipType: 'TOPIC',
    },
    {
      time: '00:47:18',
      speaker: 'Speaker 2',
      text: 'The future belongs to creators who learn how to orchestrate automated pipelines and local GPU models.',
      highlight: true,
      clipType: 'QUOTE',
    },
    {
      time: '01:12:34',
      speaker: 'Speaker 1',
      text: 'Thank you for watching and see you in the next episode of Clipping Alfa.',
      highlight: false,
    },
  ];

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
                <h3 className="text-[18px] font-bold text-[#1A1A18]">WhisperX Aligned Transcript</h3>
                <p className="text-[11px] text-[#6B6B66]">14,283 words synchronized with phonetic timestamps</p>
              </div>
            </div>

            <button
              onClick={() => toggleTranscriptDrawer(false)}
              className="w-8 h-8 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Search bar */}
          <div className="relative mb-4">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9E9E98]" />
            <input
              type="text"
              placeholder="Search words in transcript..."
              className="w-full h-10 pl-10 pr-4 rounded-full bg-white border border-[#D5D5CF] text-[12px] text-[#1A1A18] focus:outline-none focus:border-[#1A1A18]"
            />
          </div>
        </div>

        {/* Scrollable Dialogue List */}
        <div className="flex-1 overflow-y-auto pr-2 space-y-3.5 my-2">
          {sampleTranscript.map((item, i) => (
            <div
              key={i}
              className={`p-3.5 rounded-[20px] transition-all border ${
                item.highlight
                  ? 'bg-white border-[#D4F63A] shadow-sm'
                  : 'bg-white/60 border-[#D5D5CF]/60 hover:bg-white'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-bold text-[#1A1A18] flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#1A1A18]" />
                  {item.speaker}
                </span>

                <div className="flex items-center gap-2">
                  {item.clipType && (
                    <span className="px-2 py-0.5 rounded-full bg-[#D4F63A] text-[#1A1A18] text-[9px] font-bold uppercase">
                      {item.clipType} CLIP
                    </span>
                  )}
                  <button
                    onClick={() => openVideoPlayer()}
                    className="inline-flex items-center gap-1 text-[11px] font-mono text-[#6B6B66] hover:text-[#1A1A18] bg-[#EAEAE4] px-2 py-0.5 rounded-full"
                  >
                    <Play className="w-2.5 h-2.5 fill-current" />
                    {item.time}
                  </button>
                </div>
              </div>

              <p className="text-[12px] leading-relaxed text-[#3A3A36]">
                {item.text}
              </p>
            </div>
          ))}
        </div>

        {/* Footer info */}
        <div className="pt-3 border-t border-[#D5D5CF]/60 flex items-center justify-between text-[11px] text-[#6B6B66]">
          <span>Faster-Whisper model: small</span>
          <span className="font-semibold text-[#1A1A18]">avg_logprob: -0.39 (High Confidence)</span>
        </div>
      </div>
    </div>
  );
};
