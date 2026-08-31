/// <reference types="vite/client" />
import { create } from 'zustand';
import { FullProjectState, ClipItem, LogEntry, ProjectSummary } from '../types/pipeline';

interface BackendHealthInfo {
  status: string;
  service: string;
  gpu_available: boolean;
  gpu_name?: string | null;
  auth_enabled: boolean;
  version: string;
}

interface PipelineStore {
  state: FullProjectState;
  activeBottomTab: 'pipeline' | 'timeline' | 'clips' | 'transcript' | 'logs';
  
  // Conexión y Auth
  apiBaseUrl: string;
  apiToken: string;
  isConnected: boolean;
  isProcessing: boolean;
  backendHealth: BackendHealthInfo | null;
  
  // Proyectos
  projectsList: ProjectSummary[];
  activeProjectId: string | null;

  // Modales
  isNewSourceOpen: boolean;
  isVideoPlayerOpen: boolean;
  activePlayerClip: ClipItem | null;
  isTranscriptDrawerOpen: boolean;
  isLogsDrawerOpen: boolean;
  isSettingsOpen: boolean;
  isProjectsModalOpen: boolean;
  
  // Acciones
  setApiBaseUrl: (url: string) => void;
  setApiToken: (token: string) => void;
  checkBackendHealth: () => Promise<boolean>;
  
  setActiveBottomTab: (tab: 'pipeline' | 'timeline' | 'clips' | 'transcript' | 'logs') => void;
  
  openNewSourceModal: () => void;
  closeNewSourceModal: () => void;
  
  openVideoPlayer: (clip?: ClipItem) => void;
  closeVideoPlayer: () => void;
  
  toggleTranscriptDrawer: (open?: boolean) => void;
  toggleLogsDrawer: (open?: boolean) => void;
  toggleSettingsModal: (open?: boolean) => void;
  toggleProjectsModal: (open?: boolean) => void;
  
  startProcessing: (params: { youtubeUrl?: string; videoPath?: string; language?: string }) => Promise<void>;
  updateStateFromWs: (partialState: Partial<FullProjectState>) => void;
  setFullState: (newState: FullProjectState) => void;
  addLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void;
  fetchInitialState: (projectId?: string) => Promise<void>;
  fetchProjects: () => Promise<void>;
  loadProject: (projectId: string) => Promise<void>;
  getAuthHeaders: () => Record<string, string>;
  getWsUrl: () => string;
  getVideoUrl: (clip: ClipItem) => string;
  getDownloadUrl: (clip: ClipItem) => string;
}

const emptyProjectState: FullProjectState = {
  empty: true,
  source: null,
  pipeline: null,
  metrics: {
    sourceCategory: 'Ninguno',
    sourceDuration: '00:00',
    words: 0,
    candidates: 0,
    selected: 0,
    rendered: 0,
    validated: 0,
  },
  clips: [],
  logs: [],
  transcript: {
    language: 'ES',
    probability: 1.0,
    segments: [],
  },
};

const getInitialBaseUrl = (): string => {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '').trim();
  if (envUrl) return envUrl.replace(/\/+$/, '');
  const localStored = localStorage.getItem('clipping_api_base_url');
  if (localStored) return localStored.trim().replace(/\/+$/, '');
  return '';
};

const getInitialToken = (): string => {
  const envToken = (import.meta.env.VITE_API_TOKEN || '').trim();
  if (envToken) return envToken;
  const localStored = localStorage.getItem('clipping_api_token');
  return localStored ? localStored.trim() : '';
};

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  state: emptyProjectState,
  activeBottomTab: 'pipeline',
  
  apiBaseUrl: getInitialBaseUrl(),
  apiToken: getInitialToken(),
  isConnected: false,
  isProcessing: false,
  backendHealth: null,
  
  projectsList: [],
  activeProjectId: null,

  isNewSourceOpen: false,
  isVideoPlayerOpen: false,
  activePlayerClip: null,
  isTranscriptDrawerOpen: false,
  isLogsDrawerOpen: false,
  isSettingsOpen: false,
  isProjectsModalOpen: false,
  
  setApiBaseUrl: (url) => {
    const cleaned = url.trim().replace(/\/+$/, '');
    localStorage.setItem('clipping_api_base_url', cleaned);
    set({ apiBaseUrl: cleaned });
    get().fetchInitialState();
  },
  
  setApiToken: (token) => {
    const cleaned = token.trim();
    localStorage.setItem('clipping_api_token', cleaned);
    set({ apiToken: cleaned });
    get().fetchInitialState();
  },
  
  getAuthHeaders: () => {
    const { apiToken } = get();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (apiToken) {
      headers['Authorization'] = `Bearer ${apiToken}`;
      headers['X-API-Token'] = apiToken;
    }
    return headers;
  },
  
  getWsUrl: () => {
    const { apiBaseUrl, apiToken } = get();
    let url = '';
    if (apiBaseUrl) {
      if (apiBaseUrl.startsWith('https://')) {
        url = apiBaseUrl.replace('https://', 'wss://') + '/ws/pipeline';
      } else if (apiBaseUrl.startsWith('http://')) {
        url = apiBaseUrl.replace('http://', 'ws://') + '/ws/pipeline';
      } else {
        url = `wss://${apiBaseUrl}/ws/pipeline`;
      }
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      url = `${protocol}//${window.location.host}/ws/pipeline`;
    }
    if (apiToken) {
      const separator = url.includes('?') ? '&' : '?';
      url += `${separator}token=${encodeURIComponent(apiToken)}`;
    }
    return url;
  },

  getVideoUrl: (clip) => {
    const { apiBaseUrl } = get();
    if (!clip.videoUrl) return '';
    if (clip.videoUrl.startsWith('http://') || clip.videoUrl.startsWith('https://')) {
      return clip.videoUrl;
    }
    return apiBaseUrl ? `${apiBaseUrl}${clip.videoUrl}` : clip.videoUrl;
  },

  getDownloadUrl: (clip) => {
    const { apiBaseUrl } = get();
    if (!clip.downloadUrl) return '';
    if (clip.downloadUrl.startsWith('http://') || clip.downloadUrl.startsWith('https://')) {
      return clip.downloadUrl;
    }
    return apiBaseUrl ? `${apiBaseUrl}${clip.downloadUrl}` : clip.downloadUrl;
  },
  
  checkBackendHealth: async () => {
    const { apiBaseUrl } = get();
    const targetUrl = apiBaseUrl ? `${apiBaseUrl}/health` : '/health';
    try {
      const res = await fetch(targetUrl, { signal: AbortSignal.timeout(4000) });
      if (res.ok) {
        const data = await res.json();
        set({ backendHealth: data, isConnected: true });
        return true;
      }
    } catch {
      // Backend inaccesible
    }
    set({ backendHealth: null, isConnected: false });
    return false;
  },
  
  setActiveBottomTab: (tab) => {
    set({ activeBottomTab: tab });
    if (tab === 'transcript') set({ isTranscriptDrawerOpen: true });
    if (tab === 'logs') set({ isLogsDrawerOpen: true });
  },
  
  openNewSourceModal: () => set({ isNewSourceOpen: true }),
  closeNewSourceModal: () => set({ isNewSourceOpen: false }),
  
  openVideoPlayer: (clip) => set({ isVideoPlayerOpen: true, activePlayerClip: clip || null }),
  closeVideoPlayer: () => set({ isVideoPlayerOpen: false, activePlayerClip: null }),
  
  toggleTranscriptDrawer: (open) => set((s) => ({ isTranscriptDrawerOpen: open ?? !s.isTranscriptDrawerOpen })),
  toggleLogsDrawer: (open) => set((s) => ({ isLogsDrawerOpen: open ?? !s.isLogsDrawerOpen })),
  toggleSettingsModal: (open) => set((s) => ({ isSettingsOpen: open ?? !s.isSettingsOpen })),
  toggleProjectsModal: (open) => {
    const next = open ?? !get().isProjectsModalOpen;
    set({ isProjectsModalOpen: next });
    if (next) get().fetchProjects();
  },
  
  updateStateFromWs: (partialState) => {
    set((current) => ({
      state: {
        ...current.state,
        ...partialState,
        pipeline: partialState.pipeline
          ? { ...(current.state.pipeline || { download: 'pending', transcribe: 'pending', align: 'pending', select: 'pending', render: 'pending', validate: 'pending', output: 'pending' }), ...partialState.pipeline }
          : current.state.pipeline,
        metrics: partialState.metrics
          ? { ...current.state.metrics, ...partialState.metrics }
          : current.state.metrics,
      },
    }));
  },

  setFullState: (newState) => {
    set({ state: newState, isProcessing: false });
  },
  
  addLog: (log) => {
    const newEntry: LogEntry = {
      id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      timestamp: new Date().toLocaleTimeString(),
      ...log,
    };
    set((s) => ({
      state: {
        ...s.state,
        logs: [newEntry, ...s.state.logs],
      },
    }));
  },
  
  fetchInitialState: async (projectId) => {
    const { apiBaseUrl, getAuthHeaders, checkBackendHealth } = get();
    await checkBackendHealth();
    
    const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
    const targetUrl = apiBaseUrl ? `${apiBaseUrl}/api/status${query}` : `/api/status${query}`;
    
    try {
      const res = await fetch(targetUrl, {
        headers: getAuthHeaders(),
        signal: AbortSignal.timeout(6000),
      });
      if (res.ok) {
        const data = await res.json();
        set({ state: data, isConnected: true, activeProjectId: data.source?.id || null });
      } else if (res.status === 401) {
        get().addLog({
          stage: 'validate',
          type: 'warning',
          title: 'Autenticación requerida para Backend GPU',
          detail: 'Introduce tu token de acceso en Settings para conectar con el backend local.',
        });
      }
    } catch {
      // Si no se puede conectar y no hay estado previo, mantener estado vacío limpio
    }
  },

  fetchProjects: async () => {
    const { apiBaseUrl, getAuthHeaders } = get();
    const targetUrl = apiBaseUrl ? `${apiBaseUrl}/api/projects` : '/api/projects';
    try {
      const res = await fetch(targetUrl, {
        headers: getAuthHeaders(),
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        const data = await res.json();
        set({ projectsList: data.projects || [] });
      }
    } catch {
      set({ projectsList: [] });
    }
  },

  loadProject: async (projectId) => {
    await get().fetchInitialState(projectId);
    set({ isProjectsModalOpen: false });
  },
  
  startProcessing: async (params) => {
    const { apiBaseUrl, getAuthHeaders } = get();
    set({
      isProcessing: true,
      state: {
        ...get().state,
        pipeline: {
          download: 'processing',
          transcribe: 'pending',
          align: 'pending',
          select: 'pending',
          render: 'pending',
          validate: 'pending',
          output: 'pending',
        },
      },
    });
    
    get().addLog({
      stage: 'download',
      type: 'info',
      title: 'Iniciando pipeline de procesamiento real',
      detail: params.youtubeUrl ? `URL: ${params.youtubeUrl}` : `Archivo: ${params.videoPath}`,
    });
    
    const targetUrl = apiBaseUrl ? `${apiBaseUrl}/api/process` : '/api/process';
    
    try {
      const response = await fetch(targetUrl, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(params),
      });
      
      if (response.status === 401) {
        get().addLog({
          stage: 'error',
          type: 'error',
          title: 'Error de Autenticación 401',
          detail: 'El token CLIPPING_API_TOKEN no es válido. Configúralo en Settings.',
        });
        set({ isProcessing: false });
        return;
      }
      
      if (!response.ok) {
        throw new Error(`API process falló: ${response.statusText}`);
      }
    } catch (err: any) {
      get().addLog({
        stage: 'error',
        type: 'error',
        title: 'Error al enviar petición al servidor GPU',
        detail: err.message || 'Verifica la conexión del túnel o del backend local.',
      });
      set({ isProcessing: false });
    }
  },
}));
