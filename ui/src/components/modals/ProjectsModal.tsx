import React from 'react';
import { X, Folder, Clock, Film, CheckCircle2 } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const ProjectsModal: React.FC = () => {
  const { isProjectsModalOpen, toggleProjectsModal, projectsList, loadProject, activeProjectId } = usePipelineStore();

  if (!isProjectsModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg bg-[#F8F8F4] border border-[#D5D5CF] rounded-[36px] p-6 sm:p-8 shadow-2xl relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-4 border-b border-[#D5D5CF]/60 mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E5F5A4] text-[#1A1A18] flex items-center justify-center font-bold">
              <Folder className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[20px] font-bold text-[#1A1A18]">Proyectos Guardados</h2>
              <p className="text-[12px] text-[#6B6B66]">Vídeos procesados localmente en output/videos/</p>
            </div>
          </div>

          <button
            onClick={() => toggleProjectsModal(false)}
            className="w-9 h-9 rounded-full bg-white border border-[#D5D5CF] flex items-center justify-center text-[#6B6B66] hover:text-[#1A1A18] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-2.5 max-h-[55vh] overflow-y-auto pr-1">
          {projectsList.length > 0 ? (
            projectsList.map((proj) => {
              const isActive = activeProjectId === proj.id;
              return (
                <div
                  key={proj.id}
                  onClick={() => loadProject(proj.id)}
                  className={`p-3.5 rounded-[20px] border transition-all flex items-center justify-between gap-3 cursor-pointer ${
                    isActive
                      ? 'bg-white border-[#D4F63A] shadow-md ring-2 ring-[#D4F63A]/40'
                      : 'bg-white/70 border-[#D5D5CF] hover:bg-white'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-[14px] font-bold text-[#1A1A18] truncate" title={proj.title}>
                        {proj.title}
                      </h3>
                      {isActive && (
                        <span className="px-2 py-0.2 rounded-full bg-[#D4F63A] text-[#1A1A18] text-[9px] font-bold">
                          ACTIVO
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

                  <CheckCircle2 className={`w-5 h-5 ${isActive ? 'text-[#84A90A]' : 'text-gray-300'}`} />
                </div>
              );
            })
          ) : (
            <div className="p-8 text-center text-[#6B6B66]">
              <Folder className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-[13px] font-semibold">No hay proyectos procesados aún</p>
              <p className="text-[11px] mt-1">Los nuevos vídeos procesados aparecerán automáticamente aquí.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
