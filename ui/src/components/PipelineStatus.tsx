import React, { useState } from 'react';
import { Check, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';
import { StageStatus, PipelineStages } from '../types/pipeline';

type StageKey = keyof PipelineStages;

export const PipelineStatus: React.FC = () => {
  const { state, isProcessing } = usePipelineStore();
  const { pipeline } = state;
  const [isExpanded, setIsExpanded] = useState(true);

  const stages: { id: StageKey; label: string }[] = [
    { id: 'download', label: 'Descarga' },
    { id: 'transcribe', label: 'Transcripción' },
    { id: 'align', label: 'Alineación' },
    { id: 'select', label: 'Selección' },
    { id: 'render', label: 'Render 9:16' },
    { id: 'validate', label: 'Subtítulos' },
    { id: 'output', label: 'Publicación' },
  ];

  if (!pipeline) {
    return (
      <div className="w-full pt-2.5 pb-1 border-t border-[#D5D5CF]/50 flex items-center justify-between text-[11px] text-[#6B6B66]">
        <span>Pipeline inactivo</span>
        <span className="font-medium">Listo para recibir nuevo vídeo</span>
      </div>
    );
  }

  // Count completed
  const completedCount = stages.filter((s) => pipeline[s.id] === 'completed').length;
  const currentStage = stages.find((s) => pipeline[s.id] === 'processing');

  const getStatusBadge = (status: StageStatus) => {
    switch (status) {
      case 'completed':
        return (
          <div className="w-4 h-4 rounded-full bg-[#D4F63A] text-[#1A1A18] flex items-center justify-center shadow-xs">
            <Check className="w-2.5 h-2.5 stroke-[3]" />
          </div>
        );
      case 'processing':
        return (
          <div className="w-4 h-4 rounded-full bg-[#D4F63A] text-[#1A1A18] flex items-center justify-center pulse-glow shadow-xs">
            <Loader2 className="w-2.5 h-2.5 animate-spin stroke-[2.5]" />
          </div>
        );
      case 'error':
        return (
          <div className="w-4 h-4 rounded-full bg-red-500 text-white flex items-center justify-center">
            <span className="text-[9px] font-bold">!</span>
          </div>
        );
      case 'pending':
      default:
        return (
          <div className="w-4 h-4 rounded-full bg-[#D5D5CF] border border-[#BCBCB4]" />
        );
    }
  };

  return (
    <div className="w-full pt-2.5 border-t border-[#D5D5CF]/50">
      {/* Compact Header Summary */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between cursor-pointer py-1 select-none"
      >
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-bold text-[#1A1A18]">
            {isProcessing && currentStage
              ? `Procesando: ${currentStage.label}...`
              : completedCount === 7
              ? 'Pipeline Completado (7/7)'
              : `Estado del Pipeline (${completedCount}/7)`}
          </span>
          {isProcessing && (
            <span className="w-2 h-2 rounded-full bg-[#D4F63A] animate-ping" />
          )}
        </div>

        <button className="text-[#6B6B66] hover:text-[#1A1A18] transition-colors p-0.5">
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Expanded Progress Nodes */}
      {isExpanded && (
        <div className="w-full pt-2 pb-1 flex items-center justify-between overflow-x-auto no-scrollbar gap-1">
          {stages.map((stage, idx) => {
            const status = pipeline[stage.id] || 'pending';
            const isCompleted = status === 'completed';
            const isProc = status === 'processing';

            return (
              <React.Fragment key={stage.id}>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {getStatusBadge(status)}
                  <span
                    className={`text-[11px] transition-colors ${
                      isCompleted || isProc ? 'text-[#1A1A18] font-bold' : 'text-[#6B6B66]'
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>

                {idx < stages.length - 1 && (
                  <div
                    className={`flex-1 mx-1 sm:mx-2 h-[1.5px] rounded-full transition-all duration-500 min-w-[12px] ${
                      isCompleted ? 'bg-[#D4F63A]' : 'bg-[#D5D5CF]'
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      )}
    </div>
  );
};
