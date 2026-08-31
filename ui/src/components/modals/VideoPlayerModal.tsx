import React from 'react';
import { X, Download, Film, Sparkles, CheckCircle2 } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const VideoPlayerModal: React.FC = () => {
  const { isVideoPlayerOpen, closeVideoPlayer, activePlayerClip, state, getVideoUrl, getDownloadUrl } = usePipelineStore();

  if (!isVideoPlayerOpen) return null;

  const isClip = !!activePlayerClip;
  const title = isClip
    ? `${activePlayerClip.type} · (${activePlayerClip.startFormatted} — ${activePlayerClip.endFormatted})`
    : state.source?.title || 'Vídeo Fuente';

  const videoSrc = isClip && activePlayerClip ? getVideoUrl(activePlayerClip) : '';
  const downloadHref = isClip && activePlayerClip ? getDownloadUrl(activePlayerClip) : '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-3xl bg-[#1A1A18] text-white border border-[#3A3A38] rounded-[32px] sm:rounded-[36px] p-5 sm:p-7 shadow-2xl relative flex flex-col md:flex-row gap-6 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={closeVideoPlayer}
          className="absolute right-4 top-4 w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors z-20 cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Video Player Display */}
        <div className={`flex items-center justify-center bg-black rounded-[22px] overflow-hidden flex-shrink-0 border border-white/10 ${isClip ? 'w-full md:w-[280px] aspect-[9/16]' : 'w-full md:w-[480px] aspect-video'}`}>
          {videoSrc ? (
            <video
              src={videoSrc}
              controls
              autoPlay
              playsInline
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="p-6 text-center text-gray-400">
              <Film className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-[13px]">Vídeo no disponible o en proceso de renderizado</p>
            </div>
          )}
        </div>

        {/* Info Column */}
        <div className="flex-1 flex flex-col justify-between py-1">
          <div>
            <div className="flex items-center gap-2 mb-2">
              {isClip && activePlayerClip && (
                <span className="px-3 py-1 rounded-full bg-[#D4F63A] text-[#1A1A18] text-[11px] font-bold tracking-wider uppercase">
                  {activePlayerClip.type} · Confianza {activePlayerClip.scoreLabel || 'Alta'}
                </span>
              )}
            </div>

            <h3 className="text-[18px] sm:text-[20px] font-bold text-white leading-tight mb-3">
              {title}
            </h3>

            {isClip && activePlayerClip && activePlayerClip.quote && (
              <div className="bg-white/5 border border-white/10 rounded-2xl p-3.5 mb-4">
                <div className="text-[10px] font-bold text-[#D4F63A] uppercase tracking-wider mb-1 flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5" />
                  Texto del Clip
                </div>
                <p className="text-[12px] text-gray-200 italic leading-relaxed">
                  "{activePlayerClip.quote}"
                </p>
              </div>
            )}

            <div className="space-y-2 text-[12px] text-gray-300">
              <div className="flex items-center justify-between py-1 border-b border-white/5">
                <span className="text-gray-400">Duración</span>
                <span className="font-semibold font-mono">
                  {isClip && activePlayerClip
                    ? `${activePlayerClip.startFormatted} — ${activePlayerClip.endFormatted}`
                    : state.source?.durationFormatted}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-white/5">
                <span className="text-gray-400">Formato de Exportación</span>
                <span className="font-semibold">Vertical 9:16 (1080x1920)</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-white/5">
                <span className="text-gray-400">Subtítulos</span>
                <span className="font-semibold text-[#D4F63A] flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Dinámicos ASS Karaoke (Verificado)
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="pt-5 flex items-center gap-3">
            {downloadHref ? (
              <a
                href={downloadHref}
                download
                className="flex-1 h-11 rounded-full bg-[#D4F63A] hover:bg-[#C4E62A] text-[#1A1A18] font-bold text-[13px] flex items-center justify-center gap-2 transition-all shadow-md active:scale-95 cursor-pointer"
              >
                <Download className="w-4 h-4 stroke-[2.5]" />
                <span>Descargar MP4</span>
              </a>
            ) : (
              <button
                disabled
                className="flex-1 h-11 rounded-full bg-white/10 text-gray-400 font-semibold text-[13px] flex items-center justify-center gap-2 opacity-50"
              >
                <span>Descarga no disponible</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
