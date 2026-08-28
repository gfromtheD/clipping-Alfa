import React from 'react';
import { X, Folder, Network, Film, FileText, Settings } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const Header: React.FC = () => {
  const { activeNavTab, setActiveNavTab } = usePipelineStore();

  const navItems = [
    { id: 'projects', label: 'Projects', icon: Folder },
    { id: 'pipeline', label: 'Pipeline', icon: Network },
    { id: 'clips', label: 'Clips', icon: Film },
    { id: 'transcript', label: 'Transcript', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ] as const;

  return (
    <header className="w-full flex items-center justify-between py-2 sm:py-3 px-2 sm:px-4">
      {/* Left: Close/Escape Circle Button + Brand Logo + Local Pipeline Badge */}
      <div className="flex items-center gap-4 sm:gap-6">
        <button
          onClick={() => window.location.reload()}
          className="w-12 h-12 rounded-full bg-[#F8F8F4] border border-[#D5D5CF] flex items-center justify-center text-[#1A1A18] hover:bg-white hover:border-[#1A1A18] transition-all duration-200 shadow-sm active:scale-95"
          title="Reset View"
        >
          <X className="w-5 h-5 text-[#1A1A18]" />
        </button>

        <div className="flex items-center gap-3">
          <h1 className="text-[28px] sm:text-[32px] font-semibold text-[#1A1A18] tracking-tight">
            Clipping Alfa
          </h1>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#E4E4DC] rounded-full">
            <span className="w-2 h-2 rounded-full bg-[#D4F63A] animate-pulse" />
            <span className="text-[11px] font-medium tracking-wider text-[#6B6B66] uppercase">
              Local Pipeline
            </span>
          </div>
        </div>
      </div>

      {/* Right: Capsule Navigation Pills */}
      <nav className="flex items-center gap-2 sm:gap-2.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeNavTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveNavTab(item.id)}
              className={`h-11 sm:h-12 px-4 sm:px-5 rounded-full flex items-center gap-2 text-[13px] sm:text-[14px] font-medium transition-all duration-200 shadow-sm ${
                isActive
                  ? 'bg-white text-[#1A1A18] shadow-md border border-[#D5D5CF]'
                  : 'bg-[#F8F8F4] text-[#6B6B66] hover:text-[#1A1A18] hover:bg-white hover:-translate-y-0.5 border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-[#1A1A18]' : 'text-[#6B6B66]'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </header>
  );
};
