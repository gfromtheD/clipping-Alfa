import React from 'react';
import { Video, FileText, Sparkles, CheckSquare, PlayCircle, ShieldCheck } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const MetricsPanel: React.FC = () => {
  const { state } = usePipelineStore();
  const { metrics } = state;

  const metricItems = [
    {
      id: 'source',
      label: 'Source',
      value: metrics.sourceCategory,
      subValue: metrics.sourceDuration,
      icon: Video,
    },
    {
      id: 'words',
      label: 'Words',
      value: metrics.words.toLocaleString(),
      subValue: null,
      icon: FileText,
    },
    {
      id: 'candidates',
      label: 'Candidates',
      value: metrics.candidates.toString(),
      subValue: null,
      icon: Sparkles,
    },
    {
      id: 'selected',
      label: 'Selected',
      value: metrics.selected.toString(),
      subValue: null,
      icon: CheckSquare,
    },
    {
      id: 'rendered',
      label: 'Rendered',
      value: metrics.rendered.toString(),
      subValue: null,
      icon: PlayCircle,
    },
    {
      id: 'validated',
      label: 'Validated',
      value: metrics.validated.toString(),
      subValue: null,
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="w-full flex items-center justify-between gap-1 sm:gap-2">
      {metricItems.map((item, index) => {
        const Icon = item.icon;
        return (
          <React.Fragment key={item.id}>
            <div className="flex-1 flex items-center gap-2.5 sm:gap-3 py-1 px-1 sm:px-2">
              <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-[#EBEBE5] flex items-center justify-center text-[#6B6B66] flex-shrink-0">
                <Icon className="w-4 h-4 text-[#6B6B66]" />
              </div>
              <div className="min-w-0">
                <span className="block text-[11px] sm:text-[12px] font-medium text-[#6B6B66] tracking-wide">
                  {item.label}
                </span>
                <div className="flex items-baseline gap-1.5 leading-none mt-0.5">
                  <span className="text-[20px] sm:text-[24px] font-semibold text-[#1A1A18] tracking-tight">
                    {item.value}
                  </span>
                  {item.subValue && (
                    <span className="text-[11px] sm:text-[12px] text-[#6B6B66] font-normal">
                      {item.subValue}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {index < metricItems.length - 1 && (
              <div className="h-9 w-[1px] bg-[#D5D5CF]/60 flex-shrink-0 hidden md:block" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
