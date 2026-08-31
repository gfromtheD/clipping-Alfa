import React from 'react';
import { Settings, Cpu } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';

export const Header: React.FC = () => {
  const { isConnected, backendHealth, toggleSettingsModal } = usePipelineStore();

  return (
    <header className="w-full flex items-center justify-between py-2 sm:py-3 px-2 sm:px-4">
      {/* Brand & Live Connection Badge */}
      <div className="flex items-center gap-3 sm:gap-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-[14px] bg-[#1A1A18] text-[#D4F63A] flex items-center justify-center font-bold text-[18px] shadow-sm">
            α
          </div>
          <h1 className="text-[24px] sm:text-[28px] font-bold text-[#1A1A18] tracking-tight">
            Clipping Alfa
          </h1>
        </div>

        {/* Live GPU / Backend Status Pill */}
        <button
          onClick={() => toggleSettingsModal(true)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-all duration-200 cursor-pointer shadow-2xs ${
            isConnected
              ? 'bg-[#E5F5A4] text-[#1A1A18] border border-[#C2E426]'
              : 'bg-[#E4E4DC] text-[#6B6B66] hover:bg-[#DCDCD4] border border-transparent'
          }`}
          title="Configurar conexión del túnel y autenticación"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-[#7EAF00] animate-pulse' : 'bg-[#BCBCB4]'
            }`}
          />
          <span className="text-[11px] font-bold tracking-wide uppercase flex items-center gap-1">
            {isConnected ? (
              <>
                <Cpu className="w-3.5 h-3.5" />
                {backendHealth?.gpu_name
                  ? backendHealth.gpu_name.replace('NVIDIA GeForce ', '')
                  : 'GPU Conectada'}
              </>
            ) : (
              'Modo Demo (Sin GPU)'
            )}
          </span>
        </button>
      </div>

      {/* Right Side: Quick Settings & Connection Button */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => toggleSettingsModal(true)}
          className="h-10 px-4 rounded-full bg-[#F8F8F4] hover:bg-white text-[#1A1A18] border border-[#D5D5CF] text-[12px] font-semibold flex items-center gap-2 shadow-2xs transition-all duration-200"
        >
          <Settings className="w-4 h-4 text-[#6B6B66]" />
          <span>Ajustes & Conexión</span>
        </button>
      </div>
    </header>
  );
};
