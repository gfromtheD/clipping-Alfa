import React from 'react';
import { Activity, Film, FileText, ListOrdered, Folder, Settings, Plus } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const FloatingBottomDock: React.FC = () => {
  const {
    activeBottomTab,
    setActiveBottomTab,
    openNewSourceModal,
    toggleTranscriptDrawer,
    toggleLogsDrawer,
    toggleProjectsModal,
    toggleSettingsModal,
    state,
  } = usePipelineStore();

  const handleTabClick = (tab: 'pipeline' | 'timeline' | 'clips' | 'transcript' | 'logs') => {
    setActiveBottomTab(tab);
    if (tab === 'transcript') toggleTranscriptDrawer(true);
    if (tab === 'logs') toggleLogsDrawer(true);
  };

  const clipCount = state.clips.length;

  return (
    <div className="w-full flex items-center justify-center pt-3 pb-1">
      <div className="w-full max-w-5xl bg-[#F8F8F4]/95 backdrop-blur-md border border-[#D5D5CF] rounded-full px-3 sm:px-4 py-2 sm:py-2.5 flex items-center justify-between gap-3 shadow-md">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto no-scrollbar">
          {/* Timeline Tab */}
          <button
            onClick={() => handleTabClick('timeline')}
            className={`h-9 px-3.5 rounded-full flex items-center gap-1.5 text-[12px] font-semibold transition-all cursor-pointer ${
              activeBottomTab === 'timeline'
                ? 'bg-white border border-[#D5D5CF] text-[#1A1A18] shadow-xs'
                : 'text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Timeline</span>
          </button>

          {/* Clips Tab */}
          <button
            onClick={() => handleTabClick('clips')}
            className={`h-9 px-3.5 rounded-full flex items-center gap-1.5 text-[12px] font-semibold transition-all cursor-pointer ${
              activeBottomTab === 'clips'
                ? 'bg-white border border-[#D5D5CF] text-[#1A1A18] shadow-xs'
                : 'text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60'
            }`}
          >
            <Film className="w-3.5 h-3.5" />
            <span>Clips</span>
            {clipCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-[#D4F63A] text-[#1A1A18] text-[10px] font-bold">
                {clipCount}
              </span>
            )}
          </button>

          {/* Transcript Tab */}
          <button
            onClick={() => handleTabClick('transcript')}
            className="h-9 px-3.5 rounded-full flex items-center gap-1.5 text-[12px] font-semibold text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60 transition-all cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Transcripción</span>
          </button>

          {/* Logs Tab */}
          <button
            onClick={() => handleTabClick('logs')}
            className="h-9 px-3.5 rounded-full flex items-center gap-1.5 text-[12px] font-semibold text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60 transition-all cursor-pointer"
          >
            <ListOrdered className="w-3.5 h-3.5" />
            <span>Logs</span>
            {state.logs.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-[#EAEAE4] text-[#1A1A18] text-[10px] font-bold">
                {state.logs.length}
              </span>
            )}
          </button>

          {/* Projects Tab */}
          <button
            onClick={() => toggleProjectsModal(true)}
            className="h-9 px-3.5 rounded-full flex items-center gap-1.5 text-[12px] font-semibold text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60 transition-all cursor-pointer"
          >
            <Folder className="w-3.5 h-3.5" />
            <span>Proyectos</span>
          </button>
        </div>

        {/* Action Button: + Nuevo vídeo */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => toggleSettingsModal(true)}
            className="w-9 h-9 rounded-full bg-[#EAEAE4] hover:bg-[#DCDCD4] text-[#1A1A18] flex items-center justify-center transition-colors cursor-pointer"
            title="Ajustes de Conexión y Pipeline"
          >
            <Settings className="w-4 h-4" />
          </button>

          <button
            onClick={openNewSourceModal}
            className="h-9 sm:h-10 px-4 sm:px-5 rounded-full bg-[#D4F63A] hover:bg-[#C2E426] text-[#1A1A18] font-bold text-[12px] sm:text-[13px] flex items-center gap-1.5 shadow-sm hover:scale-[1.02] active:scale-95 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            <span>+ Nuevo vídeo</span>
          </button>
        </div>
      </div>
    </div>
  );
};
