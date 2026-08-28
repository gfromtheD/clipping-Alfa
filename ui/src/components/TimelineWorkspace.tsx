import React, { useRef, useState, useEffect } from 'react';
import { ChevronUp, ChevronDown, Plus, Play, Video } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const TimelineWorkspace: React.FC = () => {
  const { state, openVideoPlayer, openNewSourceModal } = usePipelineStore();
  const { clips, intro, outro } = state;
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Track positions of timeline nodes and cards to render SVG Bézier curves
  const [nodePositions, setNodePositions] = useState<{ [key: string]: { x: number; y: number } }>({});
  const [cardPositions, setCardPositions] = useState<{ [key: string]: { x: number; y: number } }>({});

  const nodeRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const cardRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  const timeMarkers = [
    { label: '00:00', percent: 8 },
    { label: '15:00', percent: 27 },
    { label: '30:00', percent: 50 },
    { label: '45:00', percent: 73 },
    { label: '60:00', percent: 92 },
  ];

  // Clip anchor percentages along the timeline matching the visual design
  const clipTimePercent = {
    clip_01: 22,
    clip_02: 47,
    clip_03: 70,
  };

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
          x: rect.left - containerRect.left + 32, // attach to top left quadrant
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
    // Cubic bezier path curving down from timeline node to card top
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
        {/* Subtle connector terminal dot */}
        <circle cx={endX} cy={endY} r="2.5" fill="#1A1A18" opacity="0.4" />
      </g>
    );
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full flex-1 bg-[#EBEBE5] border border-[#D5D5CF]/80 rounded-[32px] sm:rounded-[36px] p-6 sm:p-8 flex flex-col justify-between overflow-hidden shadow-inner min-h-[460px]"
    >
      {/* SVG Layer for Dynamic Bézier Curves */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
        {clips.map((clip) => renderBezierCurve(`node-${clip.id}`, `card-${clip.id}`))}
      </svg>

      {/* Top Bar: Time Axis & Timeline Line & Floating + Button */}
      <div className="relative w-full pt-1 pb-6">
        {/* Time Axis Labels */}
        <div className="relative w-full h-6 mb-2">
          {timeMarkers.map((marker) => (
            <div
              key={marker.label}
              className="absolute text-[12px] font-medium text-[#6B6B66] -translate-x-1/2"
              style={{ left: `${marker.percent}%` }}
            >
              {marker.label}
            </div>
          ))}
        </div>

        {/* Horizontal Timeline 1px Track Line */}
        <div className="relative w-full h-6 flex items-center">
          <div className="w-full h-[1.5px] bg-[#D5D5CF] rounded-full" />

          {/* Time Marker Tick Lines */}
          {timeMarkers.map((marker) => (
            <div
              key={`tick-${marker.label}`}
              className="absolute w-[1.5px] h-3 bg-[#BCBCB4] -top-1 -translate-x-1/2"
              style={{ left: `${marker.percent}%` }}
            />
          ))}

          {/* Intro Start Node */}
          <div
            className="absolute w-4 h-4 rounded-full bg-[#D4F63A] border-2 border-white shadow-sm flex items-center justify-center -translate-x-1/2"
            style={{ left: '8%' }}
          >
            <div className="w-1.5 h-1.5 rounded-full bg-[#1A1A18]" />
          </div>

          {/* Dynamic Nodes for each clip */}
          {clips.map((clip) => {
            const percent = clipTimePercent[clip.id as keyof typeof clipTimePercent] || 50;
            return (
              <div
                key={`node-${clip.id}`}
                ref={(el) => (nodeRefs.current[`node-${clip.id}`] = el)}
                className="absolute -translate-x-1/2 flex items-center justify-center group cursor-pointer z-20"
                style={{ left: `${percent}%` }}
                onClick={() => openVideoPlayer(clip)}
              >
                {/* Glowing Outer Halo */}
                <div className="w-6 h-6 rounded-full bg-[#D4F63A]/50 group-hover:bg-[#D4F63A]/80 flex items-center justify-center transition-all duration-300 shadow-sm">
                  <div className="w-3.5 h-3.5 rounded-full bg-[#D4F63A] border border-white flex items-center justify-center shadow">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#1A1A18]" />
                  </div>
                </div>
              </div>
            );
          })}

          {/* Outro End Node */}
          <div
            className="absolute w-4 h-4 rounded-full bg-[#D4F63A] border-2 border-white shadow-sm flex items-center justify-center -translate-x-1/2"
            style={{ left: '92%' }}
          >
            <div className="w-1.5 h-1.5 rounded-full bg-[#1A1A18]" />
          </div>
        </div>

        {/* Floating Circle + Action Button in Top Right */}
        <button
          onClick={openNewSourceModal}
          className="absolute right-0 top-0 w-13 h-13 sm:w-14 sm:h-14 rounded-full bg-[#1A1A18] text-white flex items-center justify-center shadow-lg hover:bg-black hover:scale-105 active:scale-95 transition-all duration-200 z-30"
          title="Add New Video Source"
        >
          <Plus className="w-6 h-6 stroke-[2.5]" />
        </button>
      </div>

      {/* Main Content Area: Left Controls/Intro + Center Clip Cards + Right Outro */}
      <div className="relative w-full grid grid-cols-1 md:grid-cols-12 gap-4 items-center z-20 my-auto py-2">
        {/* Left Section: Chevron Controls & Intro Capsule */}
        <div className="col-span-12 md:col-span-2 flex items-center gap-3">
          {/* Vertical Navigation Pill with Up/Down Chevrons */}
          <div className="flex flex-col items-center bg-[#F8F8F4] border border-[#D5D5CF] rounded-full p-1 shadow-sm">
            <button className="w-7 h-7 rounded-full flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white transition-colors">
              <ChevronUp className="w-4 h-4" />
            </button>
            <button className="w-7 h-7 rounded-full flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white transition-colors">
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>

          {/* Intro Segment Capsule */}
          <div className="flex-1 bg-[#F8F8F4] border border-[#D5D5CF] rounded-[24px] px-4 py-3 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#6B6B66]" />
              <span className="text-[13px] font-semibold text-[#1A1A18]">{intro.name}</span>
            </div>
            <div className="text-[11px] font-medium text-[#6B6B66]">
              {intro.startFormatted} — {intro.endFormatted}
            </div>
          </div>
        </div>

        {/* Center Section: Clip Cards (HOOK, TOPIC, QUOTE) */}
        <div className="col-span-12 md:col-span-8 flex flex-wrap lg:flex-nowrap justify-center gap-4 sm:gap-6 px-1">
          {clips.map((clip) => (
            <div
              key={clip.id}
              ref={(el) => (cardRefs.current[`card-${clip.id}`] = el)}
              className="w-full sm:w-[240px] md:w-[250px] lg:w-[260px] bg-[#F8F8F4] border border-[#D5D5CF] rounded-[26px] p-4 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between group cursor-pointer"
              onClick={() => openVideoPlayer(clip)}
            >
              {/* Card Header: Type Badge, Score Pill, Timestamp */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="px-2.5 py-0.5 rounded-full bg-[#E5F5A4] text-[#1A1A18] text-[10px] font-bold tracking-wider uppercase">
                    {clip.type}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-white border border-[#D5D5CF]/60 text-[#6B6B66] text-[11px] font-medium">
                    Score {clip.score}
                  </span>
                </div>

                <div className="text-[14px] font-semibold text-[#1A1A18] mb-2.5">
                  {clip.startFormatted}
                </div>

                {/* Media Row: Thumbnail & Quote Text */}
                <div className="flex gap-2.5 items-start mb-3">
                  {/* Thumbnail with Play Icon */}
                  <div className="relative w-20 h-16 rounded-[14px] overflow-hidden flex-shrink-0 bg-black group-hover:shadow-md transition-shadow">
                    <img
                      src={clip.thumbnail}
                      alt={clip.type}
                      className="w-full h-full object-cover opacity-90 group-hover:scale-105 transition-transform duration-300"
                    />
                    <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                      <div className="w-6 h-6 rounded-full bg-white/90 text-[#1A1A18] flex items-center justify-center pl-0.5 shadow-sm">
                        <Play className="w-2.5 h-2.5 fill-current text-[#1A1A18]" />
                      </div>
                    </div>
                  </div>

                  {/* Quote Excerpt */}
                  <p className="text-[11px] leading-[1.35] text-[#4A4A45] font-normal italic line-clamp-3">
                    "{clip.quote}"
                  </p>
                </div>
              </div>

              {/* Card Footer: Validation Dots (9:16, Subtitles, Validated) & + Button */}
              <div className="flex items-center justify-between pt-2.5 border-t border-[#D5D5CF]/50">
                <div className="flex items-center gap-2 text-[10px] font-medium text-[#6B6B66]">
                  <span className="inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#D4F63A]" />
                    9:16
                  </span>
                  <span>·</span>
                  <span className="inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#D4F63A]" />
                    Subtitles
                  </span>
                  <span>·</span>
                  <span className="inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#D4F63A]" />
                    Validated
                  </span>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    openVideoPlayer(clip);
                  }}
                  className="w-6 h-6 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18] hover:border-[#1A1A18] transition-colors"
                  title="Expand Clip"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Right Section: Outro Segment Capsule */}
        <div className="col-span-12 md:col-span-2 flex justify-end">
          <div className="w-full bg-[#F8F8F4] border border-[#D5D5CF] rounded-[24px] px-4 py-3 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="flex items-center gap-1.5 mb-1">
              <Video className="w-3.5 h-3.5 text-[#6B6B66]" />
              <span className="text-[13px] font-semibold text-[#1A1A18]">{outro.name}</span>
            </div>
            <div className="text-[11px] font-medium text-[#6B6B66]">
              {outro.startFormatted} — {outro.endFormatted}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Waveform / Visual Audio Bar */}
      <div className="w-full pt-4 flex items-center justify-center">
        <div className="w-full max-w-4xl h-5 rounded-full bg-gradient-to-r from-transparent via-[#C6E2F7]/50 to-transparent flex items-center px-4 overflow-hidden relative">
          <div className="w-full flex items-center justify-between gap-1 opacity-75">
            {Array.from({ length: 60 }).map((_, i) => (
              <div
                key={i}
                className="w-1 rounded-full transition-all duration-300"
                style={{
                  height: `${Math.max(4, Math.sin(i * 0.25) * 12 + 6)}px`,
                  backgroundColor: i >= 12 && i <= 48 ? (i % 6 === 0 ? '#D4F63A' : '#7CB7E8') : '#D5D5CF',
                }}
              />
            ))}
          </div>
          {/* Highlighted Yellow Marker Line on Waveform */}
          <div className="absolute left-[22%] top-0 bottom-0 w-[2px] bg-[#D4F63A]" />
          <div className="absolute left-[47%] top-0 bottom-0 w-[2px] bg-[#D4F63A]" />
          <div className="absolute left-[70%] top-0 bottom-0 w-[2px] bg-[#D4F63A]" />
        </div>
      </div>
    </div>
  );
};
