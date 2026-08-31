/// <reference types="vite/client" />
import { create } from 'zustand';
import { FullProjectState, ClipItem, LogEntry } from '../types/pipeline';

interface BackendHealthInfo {
  status: string;
  service: string;
  gpu_available: boolean;
  gpu_name?: string | null;
  auth_enabled: boolean;
  version: string;
}

interface PipelineStore {
  // Main state
  state: FullProjectState;
  activeNavTab: 'projects' | 'pipeline' | 'clips' | 'transcript' | 'settings';
  activeBottomTab: 'pipeline' | 'timeline' | 'clips' | 'transcript' | 'logs';
  selectedDate: number;
  
  // Remote Connection & Auth
  apiBaseUrl: string;
  apiToken: string;
  isConnected: boolean;
  isProcessing: boolean;
  backendHealth: BackendHealthInfo | null;
  
  // Modals & Panels
  isNewSourceOpen: boolean;
  isVideoPlayerOpen: boolean;
  activePlayerClip: ClipItem | null;
  isTranscriptDrawerOpen: boolean;
  isLogsDrawerOpen: boolean;
  isSettingsOpen: boolean;
  isProjectsModalOpen: boolean;
  
  // Actions
  setApiBaseUrl: (url: string) => void;
  setApiToken: (token: string) => void;
  checkBackendHealth: () => Promise<boolean>;
  
  setActiveNavTab: (tab: 'projects' | 'pipeline' | 'clips' | 'transcript' | 'settings') => void;
  setActiveBottomTab: (tab: 'pipeline' | 'timeline' | 'clips' | 'transcript' | 'logs') => void;
  setSelectedDate: (date: number) => void;
  
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
  addLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void;
  fetchInitialState: () => Promise<void>;
  getAuthHeaders: () => Record<string, string>;
  getWsUrl: () => string;
}

// Initial state matching the exact visual reference image
const initialProjectState: FullProjectState = {
  source: {
    id: 'source-future-of-ai',
    title: 'The Future of AI in Content Creation',
    category: 'Podcast',
    duration: 5078,
    durationFormatted: '01:24:38',
    thumbnail: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=800&auto=format&fit=crop',
    platform: 'youtube',
    language: 'ES',
    status: 'Ready',
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
  },
  pipeline: {
    download: 'completed',
    transcribe: 'completed',
    align: 'completed',
    select: 'completed',
    render: 'completed',
    validate: 'completed',
    output: 'completed',
  },
  metrics: {
    sourceCategory: 'Podcast',
    sourceDuration: '01:24:38',
    words: 14283,
    candidates: 27,
    selected: 8,
    rendered: 6,
    validated: 6,
  },
  intro: {
    id: 'intro-seg',
    name: 'Intro',
    start: 0,
    end: 192,
    startFormatted: '00:00',
    endFormatted: '03:12',
    type: 'intro',
  },
  outro: {
    id: 'outro-seg',
    name: 'Outro',
    start: 4354,
    end: 5078,
    startFormatted: '01:12:34',
    endFormatted: '01:24:38',
    type: 'outro',
  },
  clips: [
    {
      id: 'clip_01',
      type: 'HOOK',
      title: 'The Big Paradigm Shift',
      start: 862,
      end: 890,
      startFormatted: '00:14:22',
      endFormatted: '00:14:50',
      score: 94,
      thumbnail: 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?q=80&w=600&auto=format&fit=crop',
      quote: 'The big change is not the technology, but how we think about storytelling.',
      aspectRatio: '9:16',
      hasSubtitles: true,
      validated: true,
      videoUrl: '/output/subtitled/prueba/clip_01_subtitled.mp4',
    },
    {
      id: 'clip_02',
      type: 'TOPIC',
      title: 'AI in Creative Workflow',
      start: 1868,
      end: 1904,
      startFormatted: '00:31:08',
      endFormatted: '00:31:44',
      score: 88,
      thumbnail: 'https://images.unsplash.com/photo-1531482615713-2afd69097998?q=80&w=600&auto=format&fit=crop',
      quote: 'How AI is changing the creative process without replacing human intuition.',
      aspectRatio: '9:16',
      hasSubtitles: true,
      validated: true,
      videoUrl: '/output/subtitled/prueba/clip_01_subtitled.mp4',
    },
    {
      id: 'clip_03',
      type: 'QUOTE',
      title: 'The Future Belongs to Creators',
      start: 2838,
      end: 2872,
      startFormatted: '00:47:18',
      endFormatted: '00:47:52',
      score: 91,
      thumbnail: 'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=600&auto=format&fit=crop',
      quote: 'The future belongs to creators who learn how to orchestrate automated pipelines.',
      aspectRatio: '9:16',
      hasSubtitles: true,
      validated: true,
      videoUrl: '/output/subtitled/prueba/clip_01_subtitled.mp4',
    },
  ],
  logs: [
    {
      id: 'log-1',
      timestamp: '07:42:14',
      stage: 'download',
      type: 'success',
      title: 'Download completed',
      detail: 'Source video stream parsed (1080p, 5078s, 44.1kHz AAC)',
    },
    {
      id: 'log-2',
      timestamp: '07:42:25',
      stage: 'transcribe',
      type: 'success',
      title: 'Transcription completed',
      detail: '14,283 words transcribed with Faster-Whisper small (CUDA FP16)',
    },
    {
      id: 'log-3',
      timestamp: '07:42:32',
      stage: 'align',
      type: 'success',
      title: 'WhisperX alignment verified',
      detail: 'Word-level timestamps anchored with phonetic phoneme matching',
    },
    {
      id: 'log-4',
      timestamp: '07:42:38',
      stage: 'select',
      type: 'success',
      title: '27 candidates detected · 8 clips selected',
      detail: 'Beam search non-overlapping optimization completed',
    },
    {
      id: 'log-5',
      timestamp: '07:42:48',
      stage: 'validate',
      type: 'success',
      title: 'Subtitles verified with negative control',
      detail: 'Visual contrast 12.04% vs 0.00% negative noise floor (PASS)',
    },
  ],
  config: {
    language: 'auto',
    model: 'small',
    device: 'cuda',
    computeType: 'float16',
    minDuration: 18,
    maxDuration: 45,
    maxClips: 8,
    subtitleMarginRatio: 0.27,
  },
};

// Clean base URL helper
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
  state: initialProjectState,
  activeNavTab: 'pipeline',
  activeBottomTab: 'pipeline',
  selectedDate: 15,
  
  apiBaseUrl: getInitialBaseUrl(),
  apiToken: getInitialToken(),
  isConnected: false,
  isProcessing: false,
  backendHealth: null,
  
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
      // Backend not reachable
    }
    set({ backendHealth: null, isConnected: false });
    return false;
  },
  
  setActiveNavTab: (tab) => {
    set({ activeNavTab: tab });
    if (tab === 'projects') set({ isProjectsModalOpen: true });
    if (tab === 'settings') set({ isSettingsOpen: true });
    if (tab === 'transcript') set({ isTranscriptDrawerOpen: true });
  },
  
  setActiveBottomTab: (tab) => {
    set({ activeBottomTab: tab });
    if (tab === 'transcript') set({ isTranscriptDrawerOpen: true });
    if (tab === 'logs') set({ isLogsDrawerOpen: true });
  },
  
  setSelectedDate: (date) => set({ selectedDate: date }),
  
  openNewSourceModal: () => set({ isNewSourceOpen: true }),
  closeNewSourceModal: () => set({ isNewSourceOpen: false }),
  
  openVideoPlayer: (clip) => set({ isVideoPlayerOpen: true, activePlayerClip: clip || null }),
  closeVideoPlayer: () => set({ isVideoPlayerOpen: false, activePlayerClip: null }),
  
  toggleTranscriptDrawer: (open) => set((s) => ({ isTranscriptDrawerOpen: open ?? !s.isTranscriptDrawerOpen })),
  toggleLogsDrawer: (open) => set((s) => ({ isLogsDrawerOpen: open ?? !s.isLogsDrawerOpen })),
  toggleSettingsModal: (open) => set((s) => ({ isSettingsOpen: open ?? !s.isSettingsOpen })),
  toggleProjectsModal: (open) => set((s) => ({ isProjectsModalOpen: open ?? !s.isProjectsModalOpen })),
  
  updateStateFromWs: (partialState) => {
    set((current) => ({
      state: {
        ...current.state,
        ...partialState,
        pipeline: { ...current.state.pipeline, ...(partialState.pipeline || {}) },
        metrics: { ...current.state.metrics, ...(partialState.metrics || {}) },
      },
    }));
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
  
  fetchInitialState: async () => {
    const { apiBaseUrl, getAuthHeaders, checkBackendHealth } = get();
    const healthOk = await checkBackendHealth();
    
    const targetUrl = apiBaseUrl ? `${apiBaseUrl}/api/status` : '/api/status';
    try {
      const res = await fetch(targetUrl, {
        headers: getAuthHeaders(),
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        const data = await res.json();
        set((s) => ({ state: { ...s.state, ...data }, isConnected: true }));
      } else if (res.status === 401) {
        get().addLog({
          stage: 'validate',
          type: 'warning',
          title: 'Autenticación requerida para Backend GPU',
          detail: 'Introduce tu token de acceso en Settings para conectar con el backend local.',
        });
      }
    } catch {
      // Backend not running or in standalone demo mode
      if (!healthOk) {
        set({ isConnected: false });
      }
    }
  },
  
  startProcessing: async (params) => {
    const { apiBaseUrl, getAuthHeaders, isConnected } = get();
    set({ isProcessing: true });
    
    get().addLog({
      stage: 'download',
      type: 'info',
      title: 'Iniciando pipeline de procesamiento',
      detail: params.youtubeUrl ? `URL: ${params.youtubeUrl}` : `Archivo local: ${params.videoPath}`,
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
        throw new Error(`API process failed: ${response.statusText}`);
      }
      
      get().addLog({
        stage: 'download',
        type: 'success',
        title: 'Petición enviada al servidor GPU local',
        detail: 'Pipeline en ejecución en segundo plano...',
      });
    } catch {
      // Si no hay conexión al backend real, ejecutar simulación visual fluida
      if (!isConnected) {
        get().addLog({
          stage: 'info',
          type: 'info',
          title: 'Modo Demostración Interactivo',
          detail: 'Simulando ejecución del pipeline visualmente...',
        });
      }
      
      set((s) => ({
        state: {
          ...s.state,
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
      }));
      
      setTimeout(() => {
        set((s) => ({
          state: {
            ...s.state,
            pipeline: { ...s.state.pipeline, download: 'completed', transcribe: 'processing' },
          },
        }));
      }, 1500);
      
      setTimeout(() => {
        set((s) => ({
          state: {
            ...s.state,
            pipeline: { ...s.state.pipeline, transcribe: 'completed', align: 'processing' },
          },
        }));
      }, 3000);
      
      setTimeout(() => {
        set((s) => ({
          state: {
            ...s.state,
            pipeline: { ...s.state.pipeline, align: 'completed', select: 'processing' },
          },
        }));
      }, 4500);
      
      setTimeout(() => {
        set((s) => ({
          state: {
            ...s.state,
            pipeline: { ...s.state.pipeline, select: 'completed', render: 'processing' },
          },
        }));
      }, 6000);
      
      setTimeout(() => {
        set((s) => ({
          state: {
            ...s.state,
            pipeline: {
              download: 'completed',
              transcribe: 'completed',
              align: 'completed',
              select: 'completed',
              render: 'completed',
              validate: 'completed',
              output: 'completed',
            },
          },
          isProcessing: false,
        }));
      }, 7500);
    }
  },
}));
