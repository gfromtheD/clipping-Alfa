import React from 'react';
import { X, ListOrdered, CheckCircle2, AlertCircle, Info, Activity } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const LogsDrawer: React.FC = () => {
  const { isLogsDrawerOpen, toggleLogsDrawer, state } = usePipelineStore();
  const { logs } = state;

  if (!isLogsDrawerOpen) return null;

  const getLogIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-[#84A90A]" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-amber-500" />;
      default:
        return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg h-full bg-[#F8F8F4] border-l border-[#D5D5CF] p-6 sm:p-8 flex flex-col justify-between shadow-2xl animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div>
          <div className="flex items-center justify-between pb-4 border-b border-[#D5D5CF]/60 mb-6">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full bg-[#E5F5A4] text-[#1A1A18] flex items-center justify-center font-bold">
                <ListOrdered className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-[18px] font-bold text-[#1A1A18]">Pipeline System Logs</h3>
                <p className="text-[11px] text-[#6B6B66]">Interpreted execution trace & validation telemetry</p>
              </div>
            </div>

            <button
              onClick={() => toggleLogsDrawer(false)}
              className="w-8 h-8 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Interpreted Visual Logs Timeline */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-4 my-2">
          {logs.map((log) => (
            <div
              key={log.id}
              className="relative pl-6 pb-2 before:absolute before:left-2 before:top-4 before:bottom-0 before:w-[1.5px] before:bg-[#D5D5CF] last:before:hidden"
            >
              <div className="absolute left-0 top-0.5 w-4 h-4 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center shadow-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-[#D4F63A]" />
              </div>

              <div className="bg-white border border-[#D5D5CF]/70 rounded-[18px] p-3.5 shadow-xs">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    {getLogIcon(log.type)}
                    <span className="text-[12px] font-bold text-[#1A1A18]">
                      {log.title}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#9E9E98]">
                    {log.timestamp}
                  </span>
                </div>

                {log.detail && (
                  <p className="text-[11px] text-[#6B6B66] leading-relaxed pl-6">
                    {log.detail}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Footer info */}
        <div className="pt-3 border-t border-[#D5D5CF]/60 flex items-center justify-between text-[11px] text-[#6B6B66]">
          <span className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-[#84A90A]" />
            Pipeline Revision 4 (Stable)
          </span>
          <span className="font-mono text-[#1A1A18]">output/.work isolation OK</span>
        </div>
      </div>
    </div>
  );
};
