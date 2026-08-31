import React, { useEffect } from 'react';
import { Header } from './Header';
import { SourceCard } from './SourceCard';
import { MetricsPanel } from './MetricsPanel';
import { PipelineStatus } from './PipelineStatus';
import { TimelineWorkspace } from './TimelineWorkspace';
import { FloatingBottomDock } from './FloatingBottomDock';
import { NewSourceModal } from './modals/NewSourceModal';
import { VideoPlayerModal } from './modals/VideoPlayerModal';
import { TranscriptDrawer } from './modals/TranscriptDrawer';
import { LogsDrawer } from './modals/LogsDrawer';
import { SettingsModal } from './modals/SettingsModal';
import { ProjectsModal } from './modals/ProjectsModal';
import { usePipelineStore } from '../store/usePipelineStore';

export const AppShell: React.FC = () => {
  const {
    fetchInitialState,
    updateStateFromWs,
    setFullState,
    addLog,
    getWsUrl,
    apiBaseUrl,
    apiToken,
  } = usePipelineStore();

  useEffect(() => {
    fetchInitialState();

    const wsUrl = getWsUrl();
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'FULL_STATE_UPDATE') {
            setFullState(message.payload);
          } else if (message.type === 'STATE_UPDATE') {
            updateStateFromWs(message.payload);
          } else if (message.type === 'LOG') {
            addLog(message.payload);
          } else if (message.type === 'PIPELINE_ERROR') {
            usePipelineStore.setState({ isProcessing: false });
            addLog({
              stage: 'error',
              type: 'error',
              title: 'Error en el pipeline',
              detail: message.error || 'Ocurrió un error inesperado.',
            });
          }
        } catch {
          // Ignored
        }
      };

      ws.onerror = () => {
        // Fallback
      };
    } catch {
      // Ignored
    }

    return () => {
      if (ws) ws.close();
    };
  }, [fetchInitialState, updateStateFromWs, setFullState, addLog, getWsUrl, apiBaseUrl, apiToken]);

  return (
    <div className="w-full max-w-[1600px] min-h-[92vh] max-h-[98vh] bg-[#3B3D40] p-2.5 sm:p-4 rounded-[40px] sm:rounded-[48px] shadow-2xl flex flex-col justify-between border border-[#4F5155]/60 overflow-hidden">
      {/* Inner Dashboard Canvas */}
      <div className="w-full h-full flex-1 bg-[#F2F1ED] rounded-[32px] sm:rounded-[40px] p-4 sm:p-6 flex flex-col justify-between gap-3 sm:gap-4 shadow-inner overflow-y-auto">
        {/* 1. Header */}
        <Header />

        {/* 2. Top Area Workspace: Source Card + Metrics & Pipeline Status */}
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 items-stretch">
          {/* Source Card */}
          <div className="lg:col-span-4 flex">
            <SourceCard />
          </div>

          {/* Metrics & Pipeline Status Card */}
          <div className="lg:col-span-8 bg-[#F8F8F4] border border-[#D5D5CF]/80 rounded-[28px] sm:rounded-[32px] p-4 sm:p-5 flex flex-col justify-between shadow-xs">
            <MetricsPanel />
            <PipelineStatus />
          </div>
        </div>

        {/* 3. Central Timeline Workspace */}
        <TimelineWorkspace />

        {/* 4. Floating Bottom Dock */}
        <FloatingBottomDock />
      </div>

      {/* Modals and Drawers */}
      <NewSourceModal />
      <VideoPlayerModal />
      <TranscriptDrawer />
      <LogsDrawer />
      <SettingsModal />
      <ProjectsModal />
    </div>
  );
};
