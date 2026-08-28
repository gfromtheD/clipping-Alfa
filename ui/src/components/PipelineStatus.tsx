import React from 'react';
import { Check, Loader2 } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';
import { StageStatus } from '../types/pipeline';

export const PipelineStatus: React.FC = () => {
  const { state } = usePipelineStore();
  const { pipeline } = state;

  const stages: { id: keyof typeof pipeline; label: string }[] = [
    { id: 'download', label: 'Download' },
    { id: 'transcribe', label: 'Transcribe' },
    { id: 'align', label: 'Align' },
    { id: 'select', label: 'Select' },
    { id: 'render', label: 'Render' },
    { id: 'validate', label: 'Validate' },
    { id: 'output', label: 'Output' },
  ];

  const getStatusBadge = (status: StageStatus) => {
    switch (status) {
      case 'completed':
        return (
          <div className="w-5 h-5 rounded-full bg-[#D4F63A] text-[#1A1A18] flex items-center justify-center shadow-sm">
            <Check className="w-3 h-3 stroke-[3]" />
          </div>
        );
      case 'processing':
        return (
          <div className="w-5 h-5 rounded-full bg-[#D4F63A] text-[#1A1A18] flex items-center justify-center pulse-glow shadow-md">
            <Loader2 className="w-3 h-3 animate-spin stroke-[2.5]" />
          </div>
        );
      case 'error':
        return (
          <div className="w-5 h-5 rounded-full bg-red-400 text-white flex items-center justify-center">
            <span className="text-[10px] font-bold">!</span>
          </div>
        );
      case 'pending':
      default:
        return (
          <div className="w-5 h-5 rounded-full bg-[#D5D5CF] border border-[#BCBCB4]" />
        );
    }
  };

  return (
    <div className="w-full pt-3 pb-1 border-t border-[#D5D5CF]/50 flex items-center justify-between overflow-x-auto no-scrollbar">
      {stages.map((stage, idx) => {
        const status = pipeline[stage.id];
        const isCompleted = status === 'completed';
        const isProcessing = status === 'processing';

        return (
          <React.Fragment key={stage.id}>
            <div className="flex items-center gap-2 group cursor-default">
              {getStatusBadge(status)}
              <span
                className={`text-[12px] font-medium transition-colors ${
                  isCompleted || isProcessing ? 'text-[#1A1A18] font-semibold' : 'text-[#6B6B66]'
                }`}
              >
                {stage.label}
              </span>
            </div>

            {idx < stages.length - 1 && (
              <div
                className={`flex-1 mx-2 sm:mx-3 h-[2px] rounded-full transition-all duration-500 ${
                  isCompleted ? 'bg-[#D4F63A]' : 'bg-[#D5D5CF]'
                }`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
