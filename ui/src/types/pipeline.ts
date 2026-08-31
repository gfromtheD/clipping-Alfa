export type StageStatus = 'pending' | 'processing' | 'completed' | 'error';

export interface SourceMetadata {
  id: string;
  title: string;
  category: string;
  duration: number; // in seconds
  durationFormatted: string;
  thumbnail: string;
  platform: 'youtube' | 'local' | 'upload';
  language: string;
  status: 'Ready' | 'Processing' | 'Completed' | 'Failed';
  url?: string;
  filePath?: string;
}

export interface PipelineStages {
  download: StageStatus;
  transcribe: StageStatus;
  align: StageStatus;
  select: StageStatus;
  render: StageStatus;
  validate: StageStatus;
  output: StageStatus;
}

export interface PipelineMetrics {
  sourceCategory: string;
  sourceDuration: string;
  words: number;
  candidates: number;
  selected: number;
  rendered: number;
  validated: number;
}

export interface ClipItem {
  id: string;
  type: string;
  title?: string;
  start: number;
  end: number;
  startFormatted: string;
  endFormatted: string;
  score: number;
  scoreLabel?: string;
  thumbnail: string;
  quote: string;
  aspectRatio: '9:16' | '16:9';
  hasSubtitles: boolean;
  validated: boolean;
  videoUrl?: string;
  downloadUrl?: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  stage: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  detail?: string;
}

export interface TranscriptWord {
  word: string;
  start: number;
  end: number;
  score?: number;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  timeFormatted?: string;
  text: string;
  avg_logprob?: number;
  words?: TranscriptWord[];
}

export interface ProjectSummary {
  id: string;
  title: string;
  date: string;
  clipsCount: number;
  status: string;
}

export interface FullProjectState {
  empty: boolean;
  source: SourceMetadata | null;
  pipeline: PipelineStages | null;
  metrics: PipelineMetrics;
  clips: ClipItem[];
  logs: LogEntry[];
  transcript?: {
    language: string;
    probability: number;
    segments: TranscriptSegment[];
  };
}
