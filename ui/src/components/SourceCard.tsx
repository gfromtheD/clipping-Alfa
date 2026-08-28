import React from 'react';
import { Play, Youtube, Globe } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const SourceCard: React.FC = () => {
  const { state, openVideoPlayer } = usePipelineStore();
  const { source } = state;

  return (
    <div className="w-full bg-[#F8F8F4] border border-[#D5D5CF]/80 rounded-[28px] sm:rounded-[32px] p-4 sm:p-5 flex flex-col sm:flex-row items-center gap-4 sm:gap-5 shadow-sm hover:shadow-md transition-all duration-300">
      {/* 16:9 Thumbnail with Play Overlay */}
      <div 
        onClick={() => openVideoPlayer()}
        className="relative w-full sm:w-[150px] md:w-[170px] aspect-[16/10] sm:aspect-video rounded-[20px] overflow-hidden group cursor-pointer bg-[#1A1A18] flex-shrink-0 shadow-inner"
      >
        <img
          src={source.thumbnail}
          alt={source.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 opacity-90 group-hover:opacity-100"
        />
        <div className="absolute inset-0 bg-black/25 group-hover:bg-black/10 transition-colors flex items-center justify-center">
          <div className="w-11 h-11 rounded-full bg-white/90 group-hover:bg-white text-[#1A1A18] flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-200 backdrop-blur-sm pl-0.5">
            <Play className="w-4 h-4 fill-current text-[#1A1A18]" />
          </div>
        </div>
      </div>

      {/* Video Details & Meta */}
      <div className="flex-1 flex flex-col justify-between py-0.5 w-full min-w-0">
        <div>
          <div className="text-[12px] font-medium text-[#6B6B66] flex items-center gap-1.5 mb-1">
            <span>{source.category}</span>
            <span>·</span>
            <span>{source.durationFormatted}</span>
          </div>
          <h2 className="text-[16px] sm:text-[17px] font-semibold text-[#1A1A18] leading-tight line-clamp-2">
            {source.title}
          </h2>
        </div>

        <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#D5D5CF]/40">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1 text-[12px] text-[#6B6B66] font-medium">
              <Youtube className="w-3.5 h-3.5 text-red-600 fill-red-600" />
              YouTube
            </span>
            <span className="inline-flex items-center gap-1 text-[12px] text-[#6B6B66] font-medium">
              <Globe className="w-3.5 h-3.5 text-[#6B6B66]" />
              {source.language}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[#1A1A18]">
            <span className="w-2 h-2 rounded-full bg-[#D4F63A] ring-4 ring-[#D4F63A]/20 animate-pulse" />
            <span>{source.status}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
