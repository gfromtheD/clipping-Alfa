import React from 'react';
import { Play, Youtube, Globe, Plus, Video } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const SourceCard: React.FC = () => {
  const { state, openNewSourceModal, openVideoPlayer } = usePipelineStore();
  const { source, empty } = state;

  if (empty || !source) {
    return (
      <div className="w-full bg-[#F8F8F4] border border-[#D5D5CF]/80 rounded-[28px] sm:rounded-[32px] p-5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xs">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-[18px] bg-[#EAEAE4] text-[#6B6B66] flex items-center justify-center">
            <Video className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-[15px] font-bold text-[#1A1A18]">Aún no hay vídeo procesado</h2>
            <p className="text-[12px] text-[#6B6B66]">Pega un enlace de YouTube o usa un vídeo local para generar clips 9:16.</p>
          </div>
        </div>

        <button
          onClick={openNewSourceModal}
          className="h-11 px-5 rounded-full bg-[#D4F63A] hover:bg-[#C2E426] text-[#1A1A18] font-bold text-[13px] flex items-center gap-2 shadow-sm transition-all duration-200 cursor-pointer"
        >
          <Plus className="w-4 h-4 stroke-[3]" />
          <span>+ Nuevo vídeo</span>
        </button>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#F8F8F4] border border-[#D5D5CF]/80 rounded-[28px] sm:rounded-[32px] p-4 sm:p-5 flex flex-col sm:flex-row items-center justify-between gap-4 sm:gap-5 shadow-xs">
      <div className="flex flex-col sm:flex-row items-center gap-4 flex-1 min-w-0">
        {/* 16:9 Thumbnail preview */}
        <div 
          onClick={() => openVideoPlayer()}
          className="relative w-full sm:w-[130px] md:w-[150px] aspect-video rounded-[18px] overflow-hidden group cursor-pointer bg-[#1A1A18] flex-shrink-0 shadow-inner"
        >
          <img
            src={source.thumbnail}
            alt={source.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 opacity-90 group-hover:opacity-100"
          />
          <div className="absolute inset-0 bg-black/25 group-hover:bg-black/10 transition-colors flex items-center justify-center">
            <div className="w-9 h-9 rounded-full bg-white/90 group-hover:bg-white text-[#1A1A18] flex items-center justify-center shadow-md pl-0.5">
              <Play className="w-3.5 h-3.5 fill-current text-[#1A1A18]" />
            </div>
          </div>
        </div>

        {/* Video Info */}
        <div className="flex-1 min-w-0 text-center sm:text-left">
          <div className="text-[11px] font-medium text-[#6B6B66] flex items-center justify-center sm:justify-start gap-1.5 mb-1">
            <span>{source.category}</span>
            <span>·</span>
            <span className="font-semibold text-[#1A1A18]">{source.durationFormatted}</span>
          </div>
          <h2 className="text-[15px] sm:text-[16px] font-bold text-[#1A1A18] leading-tight truncate" title={source.title}>
            {source.title}
          </h2>

          <div className="flex items-center justify-center sm:justify-start gap-3 mt-2">
            <span className="inline-flex items-center gap-1 text-[11px] text-[#6B6B66] font-medium">
              <Youtube className="w-3.5 h-3.5 text-red-600 fill-red-600" />
              {source.platform === 'youtube' ? 'YouTube' : 'Local'}
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] text-[#6B6B66] font-medium">
              <Globe className="w-3.5 h-3.5 text-[#6B6B66]" />
              {source.language}
            </span>
          </div>
        </div>
      </div>

      {/* Single CTA Button */}
      <button
        onClick={openNewSourceModal}
        className="h-10 sm:h-11 px-5 rounded-full bg-[#D4F63A] hover:bg-[#C2E426] text-[#1A1A18] font-bold text-[13px] flex items-center gap-2 shadow-xs transition-all duration-200 cursor-pointer flex-shrink-0"
      >
        <Plus className="w-4 h-4 stroke-[3]" />
        <span>+ Nuevo vídeo</span>
      </button>
    </div>
  );
};
