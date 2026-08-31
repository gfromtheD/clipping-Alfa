import React, { useRef, useState, useEffect } from 'react';
import { Play, Download, Film, CheckCircle2 } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const TimelineWorkspace: React.FC = () => {
  const { state, openVideoPlayer, openNewSourceModal, getDownloadUrl } = usePipelineStore();
  const { source, clips, empty } = state;
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [nodePositions, setNodePositions] = useState<{ [key: string]: { x: number; y: number } }>({});
  const [cardPositions, setCardPositions] = useState<{ [key: string]: { x: number; y: number } }>({});

  const nodeRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const cardRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  // Dynamic time marker generation based on actual video duration
  const duration = source?.duration || 60;
  const generateTimeMarkers = () => {
    const count = 5;
    const markers = [];
    for (let i = 0; i < count; i++) {
      const fraction = i / (count - 1);
      const sec = fraction * duration;
      const mins = Math.floor(sec / 60);
      const secs = Math.floor(sec % 60);
      const label = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      markers.push({
        label,
        percent: fraction * 100,
      });
    }
    return markers;
  };

  const timeMarkers = generateTimeMarkers();

  const updatePositions = () => {
    if (!containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();

    const newNodes: { [key: string]: { x: number; y: number } } = {};
    const newCards: { [key: string]: { x: number; y: number } } = {};

    Object.entries(nodeRefs.current).forEach(([id, el]) => {
      if (el) {
        const rect = el.getBoundingClientRect();
        newNodes[id] = {
          x: rect.left - containerRect.left + rect.width / 2,
          y: rect.top - containerRect.top + rect.height / 2,
        };
      }
    });

    Object.entries(cardRefs.current).forEach(([id, el]) => {
      if (el) {
        const rect = el.getBoundingClientRect();
        newCards[id] = {
          x: rect.left - containerRect.left + rect.width / 2,
          y: rect.top - containerRect.top,
        };
      }
    });

    setNodePositions(newNodes);
    setCardPositions(newCards);
  };

  useEffect(() => {
    updatePositions();
    window.addEventListener('resize', updatePositions);
    const timer = setTimeout(updatePositions, 100);
    return () => {
      window.removeEventListener('resize', updatePositions);
      clearTimeout(timer);
    };
  }, [clips]);

  const renderBezierCurve = (nodeId: string, cardId: string) => {
    const node = nodePositions[nodeId];
    const card = cardPositions[cardId];
    if (!node || !card) return null;

    const startX = node.x;
    const startY = node.y;
    const endX = card.x;
    const endY = card.y;

    const deltaY = endY - startY;
    const controlY1 = startY + deltaY * 0.45;
    const controlY2 = startY + deltaY * 0.55;

    const pathData = `M ${startX} ${startY} C ${startX} ${controlY1}, ${endX} ${controlY2}, ${endX} ${endY}`;

    return (
      <g key={`connector-${nodeId}-${cardId}`}>
        <path
          d={pathData}
          fill="none"
          stroke="#C8C8C0"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <circle cx={endX} cy={endY} r="2.5" fill="#1A1A18" opacity="0.4" />
      </g>
    );
  };

  // Empty state placeholder
  if (empty || !source || clips.length === 0) {
    return (
      <div className="w-full flex-1 bg-[#EBEBE5] border border-[#D5D5CF]/80 rounded-[32px] sm:rounded-[36px] p-8 flex flex-col items-center justify-center text-center min-h-[420px] shadow-inner">
        <div className="w-16 h-16 rounded-[22px] bg-white text-[#1A1A18] flex items-center justify-center shadow-xs mb-3">
          <Film className="w-8 h-8 text-[#6B6B66]" />
        </div>
        <h3 className="text-[18px] font-bold text-[#1A1A18] mb-1">
          No hay clips seleccionados aún
        </h3>
        <p className="text-[13px] text-[#6B6B66] max-w-md mb-5">
          Procesa un vídeo para que la IA extraiga los mejores momentos, genere los timestamps y renderice los clips verticales con subtítulos dinámicos.
        </p>
        <button
          onClick={openNewSourceModal}
          className="h-11 px-6 rounded-full bg-[#D4F63A] hover:bg-[#C2E426] text-[#1A1A18] font-bold text-[13px] shadow-sm transition-all cursor-pointer"
        >
          + Añadir primer vídeo
        </button>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full flex-1 bg-[#EBEBE5] border border-[#D5D5CF]/80 rounded-[32px] sm:rounded-[36px] p-6 sm:p-7 flex flex-col justify-between overflow-hidden shadow-inner min-h-[440px]"
    >
      {/* SVG Layer for dynamic Bézier curves */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
        {clips.map((clip) => renderBezierCurve(`node-${clip.id}`, `card-${clip.id}`))}
      </svg>

      {/* Top Bar: Time Axis & Dynamic Nodes */}
      <div className="relative w-full pt-1 pb-4">
        {/* Dynamic Time Markers */}
        <div className="relative w-full h-6 mb-2">
          {timeMarkers.map((marker, i) => (
            <div
              key={`marker-${i}`}
              className="absolute text-[11px] font-medium text-[#6B6B66] -translate-x-1/2"
              style={{ left: `${Math.min(95, Math.max(5, marker.percent))}%` }}
            >
              {marker.label}
            </div>
          ))}
        </div>

        {/* Horizontal Timeline Track Line */}
        <div className="relative w-full h-6 flex items-center">
          <div className="w-full h-[2px] bg-[#D5D5CF] rounded-full" />

          {/* Time Marker Tick Lines */}
          {timeMarkers.map((marker, i) => (
            <div
              key={`tick-${i}`}
              className="absolute w-[1.5px] h-3 bg-[#BCBCB4] -top-1 -translate-x-1/2"
              style={{ left: `${Math.min(95, Math.max(5, marker.percent))}%` }}
            />
          ))}

          {/* Dynamic Nodes for each clip */}
          {clips.map((clip) => {
            const percent = duration > 0 ? Math.min(92, Math.max(8, (clip.start / duration) * 100)) : 50;
            return (
              <div
                key={`node-${clip.id}`}
                ref={(el) => (nodeRefs.current[`node-${clip.id}`] = el)}
                className="absolute -translate-x-1/2 flex items-center justify-center group cursor-pointer z-20"
                style={{ left: `${percent}%` }}
                onClick={() => openVideoPlayer(clip)}
              >
                <div className="w-6 h-6 rounded-full bg-[#D4F63A]/60 group-hover:bg-[#D4F63A] flex items-center justify-center transition-all duration-300 shadow-xs">
                  <div className="w-3.5 h-3.5 rounded-full bg-[#D4F63A] border border-white flex items-center justify-center shadow-xs">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#1A1A18]" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Center Section: Real Clip Cards */}
      <div className="relative w-full flex flex-wrap justify-center gap-4 sm:gap-6 px-1 z-20 my-auto py-2">
        {clips.map((clip) => (
          <div
            key={clip.id}
            ref={(el) => (cardRefs.current[`card-${clip.id}`] = el)}
            className="w-full sm:w-[260px] md:w-[280px] bg-[#F8F8F4] border border-[#D5D5CF] rounded-[24px] p-4 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between"
          >
            <div>
              {/* Header: Type Badge, Confidence Pill */}
              <div className="flex items-center justify-between mb-2">
                <span className="px-2.5 py-0.5 rounded-full bg-[#E5F5A4] text-[#1A1A18] text-[10px] font-bold tracking-wider uppercase">
                  {clip.type}
                </span>
                <span className="px-2 py-0.5 rounded-full bg-white border border-[#D5D5CF]/60 text-[#6B6B66] text-[10px] font-semibold">
                  Confianza: {clip.scoreLabel || 'Alta'}
                </span>
              </div>

              {/* Time Range */}
              <div className="text-[13px] font-bold text-[#1A1A18] mb-2">
                {clip.startFormatted} — {clip.endFormatted}
              </div>

              {/* Quote Excerpt */}
              <p className="text-[12px] leading-relaxed text-[#3A3A36] italic line-clamp-3 mb-3 bg-white/50 p-2 rounded-[14px] border border-[#D5D5CF]/40">
                "{clip.quote || 'Highlight extraído automáticamente...'}"
              </p>
            </div>

            {/* Footer: Publication Check & Action Buttons */}
            <div className="pt-2.5 border-t border-[#D5D5CF]/60 space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#84A90A]">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Listo para publicar (9:16 + Subtítulos)</span>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => openVideoPlayer(clip)}
                  className="flex-1 h-8 rounded-full bg-[#1A1A18] hover:bg-black text-white text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>Reproducir</span>
                </button>

                <a
                  href={getDownloadUrl(clip)}
                  download
                  className="h-8 px-3 rounded-full bg-white hover:bg-[#EAEAE4] border border-[#D5D5CF] text-[#1A1A18] text-[11px] font-semibold flex items-center justify-center gap-1 transition-colors"
                  title="Descargar vídeo vertical con subtítulos"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>MP4</span>
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Audio/Speech Waves Bar */}
      <div className="w-full pt-2 flex items-center justify-center">
        <div className="w-full max-w-2xl h-4 rounded-full bg-[#DCDCD6] flex items-center px-3 overflow-hidden opacity-80">
          <div className="w-full flex items-center justify-between gap-1">
            {Array.from({ length: 48 }).map((_, i) => (
              <div
                key={i}
                className="w-1 rounded-full transition-all"
                style={{
                  height: `${Math.max(3, Math.sin(i * 0.3) * 10 + 4)}px`,
                  backgroundColor: i % 4 === 0 ? '#D4F63A' : '#A4A49E',
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
