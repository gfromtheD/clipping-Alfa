import React from 'react';
import { X, Folder, Clock, Film, CheckCircle2 } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const ProjectsModal: React.FC = () => {
  const { isProjectsModalOpen, toggleProjectsModal, state } = usePipelineStore();

  if (!isProjectsModalOpen) return null;

  const projectList = [
    {
      id: 'proj-1',
      title: 'The Future of AI in Content Creation',
      date: 'Aug 28, 2026',
      clipsCount: 6,
      status: 'Ready',
      active: true,
      thumbnail: state.source.thumbnail,
    },
    {
      id: 'proj-2',
      title: 'Prueba Video Synthesized Test',
      date: 'Aug 27, 2026',
      clipsCount: 1,
      status: 'Completed',
      active: false,
      thumbnail: 'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?q=80&w=600&auto=format&fit=crop',
    },
    {
      id: 'proj-3',
      title: 'Generative Audio & Phonetic Alignment Podcast',
      date: 'Aug 25, 2026',
      clipsCount: 8,
      status: 'Completed',
      active: false,
      thumbnail: 'https://images.unsplash.com/photo-1590602847861-f357a9332bbc?q=80&w=600&auto=format&fit=crop',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-xl bg-[#F8F8F4] border border-[#D5D5CF] rounded-[36px] p-6 sm:p-8 shadow-2xl relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-4 border-b border-[#D5D5CF]/60 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E5F5A4] text-[#1A1A18] flex items-center justify-center font-bold">
              <Folder className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[20px] font-bold text-[#1A1A18]">Processed Projects</h2>
              <p className="text-[12px] text-[#6B6B66]">Manage previous video ingestion sessions</p>
            </div>
          </div>

          <button
            onClick={() => toggleProjectsModal(false)}
            className="w-9 h-9 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
          {projectList.map((proj) => (
            <div
              key={proj.id}
              className={`p-4 rounded-[22px] border transition-all flex items-center gap-4 cursor-pointer ${
                proj.active
                  ? 'bg-white border-[#D4F63A] shadow-md ring-2 ring-[#D4F63A]/30'
                  : 'bg-white/60 border-[#D5D5CF] hover:bg-white'
              }`}
            >
              <div className="w-16 h-12 rounded-[14px] overflow-hidden bg-black flex-shrink-0">
                <img src={proj.thumbnail} alt={proj.title} className="w-full h-full object-cover" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-[14px] font-bold text-[#1A1A18] truncate">{proj.title}</h3>
                  {proj.active && (
                    <span className="px-2 py-0.5 rounded-full bg-[#D4F63A] text-[#1A1A18] text-[9px] font-bold">
                      ACTIVE
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-[11px] text-[#6B6B66]">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {proj.date}
                  </span>
                  <span>·</span>
                  <span className="flex items-center gap-1">
                    <Film className="w-3 h-3" />
                    {proj.clipsCount} clips
                  </span>
                </div>
              </div>

              <CheckCircle2 className={`w-5 h-5 ${proj.active ? 'text-[#84A90A]' : 'text-gray-300'}`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
