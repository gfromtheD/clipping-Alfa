import React from 'react';
import { FileText, Sparkles, CheckSquare, PlayCircle, ShieldCheck } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const MetricsPanel: React.FC = () => {
  const { state } = usePipelineStore();
  const { metrics, empty } = state;

  const metricItems = [
    {
      id: 'words',
      label: 'Palabras',
      value: empty ? '—' : metrics.words.toLocaleString(),
      icon: FileText,
    },
    {
      id: 'candidates',
      label: 'Candidatos',
      value: empty ? '—' : metrics.candidates.toString(),
      icon: Sparkles,
    },
    {
      id: 'selected',
      label: 'Seleccionados',
      value: empty ? '—' : metrics.selected.toString(),
      icon: CheckSquare,
    },
    {
      id: 'rendered',
      label: 'Render 9:16',
      value: empty ? '—' : metrics.rendered.toString(),
      icon: PlayCircle,
    },
    {
      id: 'validated',
      label: 'Validados (PASS)',
      value: empty ? '—' : metrics.validated.toString(),
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="w-full flex items-center justify-between gap-1 sm:gap-2">
      {metricItems.map((item, index) => {
        const Icon = item.icon;
        return (
          <React.Fragment key={item.id}>
            <div className="flex-1 flex items-center gap-2 sm:gap-2.5 py-1 px-1">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-[#EBEBE5] flex items-center justify-center text-[#6B6B66] flex-shrink-0">
                <Icon className="w-3.5 h-3.5 text-[#6B6B66]" />
              </div>
              <div className="min-w-0">
                <span className="block text-[10px] sm:text-[11px] font-medium text-[#6B6B66] tracking-wide truncate">
                  {item.label}
                </span>
                <div className="flex items-baseline gap-1.5 leading-none mt-0.5">
                  <span className="text-[18px] sm:text-[20px] font-bold text-[#1A1A18] tracking-tight">
                    {item.value}
                  </span>
                </div>
              </div>
            </div>

            {index < metricItems.length - 1 && (
              <div className="h-8 w-[1px] bg-[#D5D5CF]/60 flex-shrink-0 hidden lg:block" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
