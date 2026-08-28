import React from 'react';
import {
  Calendar,
  Network,
  Activity,
  Film,
  FileText,
  ListOrdered,
  Cloud,
  Link2,
  Copy,
  Maximize2,
  Plus,
} from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const FloatingBottomDock: React.FC = () => {
  const {
    activeBottomTab,
    setActiveBottomTab,
    selectedDate,
    setSelectedDate,
    openNewSourceModal,
    toggleTranscriptDrawer,
    toggleLogsDrawer,
  } = usePipelineStore();

  const days = [12, 13, 14, 15, 16, 17, 18];

  const handleTabClick = (tab: 'pipeline' | 'timeline' | 'clips' | 'transcript' | 'logs') => {
    setActiveBottomTab(tab);
    if (tab === 'transcript') toggleTranscriptDrawer(true);
    if (tab === 'logs') toggleLogsDrawer(true);
  };

  return (
    <div className="w-full flex items-center justify-center pt-3 pb-1">
      <div className="w-full max-w-7xl bg-[#F8F8F4]/95 backdrop-blur-md border border-[#D5D5CF] rounded-full px-3 sm:px-4 py-2 sm:py-2.5 flex flex-wrap items-center justify-between gap-3 shadow-float">
        {/* Left: Calendar & Date Selector */}
        <div className="flex items-center gap-3 sm:gap-4 pl-1">
          {/* Calendar Icon Button */}
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-[#1A1A18] text-white flex items-center justify-center shadow-sm">
            <Calendar className="w-4 h-4" />
          </div>

          {/* Month Label */}
          <div className="text-[12px] sm:text-[13px] font-semibold text-[#1A1A18] whitespace-nowrap hidden lg:block">
            May 2025
          </div>

          <div className="h-6 w-[1px] bg-[#D5D5CF] hidden lg:block" />

          {/* Days Pills Row */}
          <div className="flex items-center gap-1 sm:gap-1.5 overflow-x-auto no-scrollbar">
            {days.map((day) => {
              const isSelected = selectedDate === day;
              return (
                <button
                  key={day}
                  onClick={() => setSelectedDate(day)}
                  className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full text-[12px] font-medium transition-all duration-200 flex items-center justify-center ${
                    isSelected
                      ? 'bg-[#D4F63A] text-[#1A1A18] font-bold shadow-sm scale-105'
                      : 'text-[#6B6B66] hover:text-[#1A1A18] hover:bg-[#EAEAE4]'
                  }`}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>

        {/* Center: Main View Navigation Tabs */}
        <div className="flex items-center gap-1 sm:gap-2">
          {/* Pipeline Tab */}
          <button
            onClick={() => handleTabClick('pipeline')}
            className={`h-9 sm:h-10 px-3 sm:px-4 rounded-full flex items-center gap-1.5 text-[12px] sm:text-[13px] font-medium transition-all ${
              activeBottomTab === 'pipeline'
                ? 'bg-white border border-[#D5D5CF] text-[#1A1A18] shadow-sm'
                : 'text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>Pipeline</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#D4F63A]" />
          </button>

          {/* Timeline Tab */}
          <button
            onClick={() => handleTabClick('timeline')}
            className={`h-9 sm:h-10 px-3 sm:px-4 rounded-full flex items-center gap-1.5 text-[12px] sm:text-[13px] font-medium transition-all ${
              activeBottomTab === 'timeline'
                ? 'bg-white border border-[#D5D5CF] text-[#1A1A18] shadow-sm'
                : 'text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Timeline</span>
          </button>

          {/* Clips Tab */}
          <button
            onClick={() => handleTabClick('clips')}
            className={`h-9 sm:h-10 px-3 sm:px-4 rounded-full flex items-center gap-1.5 text-[12px] sm:text-[13px] font-medium transition-all ${
              activeBottomTab === 'clips'
                ? 'bg-white border border-[#D5D5CF] text-[#1A1A18] shadow-sm'
                : 'text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60'
            }`}
          >
            <Film className="w-3.5 h-3.5" />
            <span>Clips</span>
            <span className="px-1.5 py-0.2 rounded-full bg-[#D4F63A] text-[#1A1A18] text-[10px] font-bold">
              6
            </span>
          </button>

          {/* Transcript Tab */}
          <button
            onClick={() => handleTabClick('transcript')}
            className={`h-9 sm:h-10 px-3 sm:px-4 rounded-full flex items-center gap-1.5 text-[12px] sm:text-[13px] font-medium transition-all ${
              activeBottomTab === 'transcript'
                ? 'bg-white border border-[#D5D5CF] text-[#1A1A18] shadow-sm'
                : 'text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Transcript</span>
          </button>

          {/* Logs Tab */}
          <button
            onClick={() => handleTabClick('logs')}
            className={`h-9 sm:h-10 px-3 sm:px-4 rounded-full flex items-center gap-1.5 text-[12px] sm:text-[13px] font-medium transition-all ${
              activeBottomTab === 'logs'
                ? 'bg-white border border-[#D5D5CF] text-[#1A1A18] shadow-sm'
                : 'text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white/60'
            }`}
          >
            <ListOrdered className="w-3.5 h-3.5" />
            <span>Logs</span>
            <span className="px-1.5 py-0.2 rounded-full bg-[#D4F63A] text-[#1A1A18] text-[10px] font-bold">
              3
            </span>
          </button>
        </div>

        {/* Right: Quick Tools Cluster & Primary CTA Button */}
        <div className="flex items-center gap-2.5 pr-1">
          {/* Dark Tool Capsule with 4 Action Icons */}
          <div className="hidden sm:flex items-center gap-1 bg-[#1A1A18] rounded-full px-3 py-1.5 text-white shadow-sm">
            <button className="w-7 h-7 rounded-full flex items-center justify-center text-gray-300 hover:text-white hover:bg-white/10 transition-colors" title="Cloud Sync">
              <Cloud className="w-3.5 h-3.5" />
            </button>
            <button className="w-7 h-7 rounded-full flex items-center justify-center text-gray-300 hover:text-white hover:bg-white/10 transition-colors" title="Copy Link">
              <Link2 className="w-3.5 h-3.5" />
            </button>
            <button className="w-7 h-7 rounded-full flex items-center justify-center text-gray-300 hover:text-white hover:bg-white/10 transition-colors" title="Export Data">
              <Copy className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => {
                if (!document.fullscreenElement) {
                  document.documentElement.requestFullscreen();
                } else {
                  document.exitFullscreen();
                }
              }}
              className="w-7 h-7 rounded-full flex items-center justify-center text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
              title="Fullscreen"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Primary CTA: + New Source Button */}
          <button
            onClick={openNewSourceModal}
            className="h-10 sm:h-11 px-5 sm:px-6 rounded-full bg-[#D4F63A] hover:bg-[#C2E426] text-[#1A1A18] font-bold text-[13px] sm:text-[14px] flex items-center gap-2 shadow-md hover:shadow-glow hover:scale-[1.02] active:scale-95 transition-all duration-200"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            <span>New Source</span>
          </button>
        </div>
      </div>
    </div>
  );
};
