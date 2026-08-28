import React from 'react';
import { X, Download, Share2, Sparkles, CheckCircle2 } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const VideoPlayerModal: React.FC = () => {
  const { isVideoPlayerOpen, closeVideoPlayer, activePlayerClip, state } = usePipelineStore();

  if (!isVideoPlayerOpen) return null;

  const isClip = !!activePlayerClip;
  const title = isClip ? `${activePlayerClip.type} Clip (${activePlayerClip.startFormatted})` : state.source.title;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-4xl bg-[#1A1A18] text-white border border-[#3A3A38] rounded-[36px] p-6 sm:p-8 shadow-2xl relative flex flex-col md:flex-row gap-6 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={closeVideoPlayer}
          className="absolute right-5 top-5 w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors z-20"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Video Player Display */}
        <div className={`flex items-center justify-center bg-black/80 rounded-[26px] overflow-hidden flex-shrink-0 border border-white/10 ${isClip ? 'w-full md:w-[280px] aspect-[9/16]' : 'w-full md:w-[520px] aspect-video'}`}>
          <div className="relative w-full h-full flex flex-col items-center justify-center p-4 text-center">
            {/* Visual Demo Poster with Animated Badge */}
            <img
              src={isClip ? activePlayerClip.thumbnail : state.source.thumbnail}
              alt="Video Preview"
              className="absolute inset-0 w-full h-full object-cover opacity-60"
            />
            <div className="relative z-10 bg-black/60 backdrop-blur-md p-4 rounded-2xl border border-white/10 max-w-[90%]">
              <div className="w-12 h-12 rounded-full bg-[#D4F63A] text-[#1A1A18] flex items-center justify-center mx-auto mb-2 font-bold shadow-glow">
                ▶
              </div>
              <p className="text-[13px] font-semibold text-white mb-1">
                {isClip ? `${activePlayerClip.type} Vertical 1080x1920` : 'Source Horizontal Video'}
              </p>
              {isClip && (
                <p className="text-[11px] text-[#D4F63A] italic">
                  "{activePlayerClip.quote}"
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Info & Action Column */}
        <div className="flex-1 flex flex-col justify-between py-2">
          <div>
            <div className="flex items-center gap-2 mb-2">
              {isClip ? (
                <span className="px-3 py-1 rounded-full bg-[#D4F63A] text-[#1A1A18] text-[11px] font-bold tracking-wider uppercase">
                  {activePlayerClip.type} · Score {activePlayerClip.score}
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full bg-white/10 text-white text-[11px] font-medium">
                  Full Source Video
                </span>
              )}
            </div>

            <h3 className="text-[20px] sm:text-[22px] font-bold text-white leading-tight mb-3">
              {title}
            </h3>

            {isClip && (
              <div className="bg-white/5 border border-white/10 rounded-2xl p-4 mb-4">
                <div className="text-[11px] font-semibold text-[#D4F63A] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  Recognized Hook / Quote
                </div>
                <p className="text-[13px] text-gray-200 italic leading-relaxed">
                  "{activePlayerClip.quote}"
                </p>
              </div>
            )}

            <div className="space-y-2 text-[12px] text-gray-300">
              <div className="flex items-center justify-between py-1 border-b border-white/5">
                <span className="text-gray-400">Duration</span>
                <span className="font-semibold">{isClip ? `${activePlayerClip.startFormatted} — ${activePlayerClip.endFormatted}` : state.source.durationFormatted}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-white/5">
                <span className="text-gray-400">Resolution & Codec</span>
                <span className="font-semibold">{isClip ? '1080x1920 (libx264)' : '1920x1080 (AAC Audio)'}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-white/5">
                <span className="text-gray-400">Subtitles Layer</span>
                <span className="font-semibold text-[#D4F63A] flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Dynamic ASS Karaoke (\k)
                </span>
              </div>
            </div>
          </div>

          <div className="pt-6 flex items-center gap-3">
            <button
              onClick={() => alert(`Descargando ${isClip ? activePlayerClip.id : 'video_source'}.mp4`)}
              className="flex-1 h-11 rounded-full bg-[#D4F63A] hover:bg-[#C4E62A] text-[#1A1A18] font-bold text-[13px] flex items-center justify-center gap-2 transition-all shadow-md active:scale-95"
            >
              <Download className="w-4 h-4 stroke-[2.5]" />
              <span>Download MP4</span>
            </button>

            <button
              onClick={() => alert('Enlace copiado al portapapeles')}
              className="h-11 px-4 rounded-full bg-white/10 hover:bg-white/20 text-white text-[13px] font-medium flex items-center gap-2 transition-colors"
            >
              <Share2 className="w-4 h-4" />
              <span>Share</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
