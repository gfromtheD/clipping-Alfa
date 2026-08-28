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
  type: 'HOOK' | 'TOPIC' | 'QUOTE' | 'STORY' | 'INSIGHT';
  title?: string;
  start: number; // seconds
  end: number;   // seconds
  startFormatted: string;
  endFormatted: string;
  score: number;
  thumbnail: string;
  quote: string;
  aspectRatio: '9:16' | '16:9';
  hasSubtitles: boolean;
  validated: boolean;
  videoUrl?: string;
  assUrl?: string;
}

export interface TimelineSegment {
  id: string;
  name: string;
  start: number;
  end: number;
  startFormatted: string;
  endFormatted: string;
  type: 'intro' | 'outro' | 'content';
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
  text: string;
  avg_logprob?: number;
  words?: TranscriptWord[];
}

export interface FullProjectState {
  source: SourceMetadata;
  pipeline: PipelineStages;
  metrics: PipelineMetrics;
  clips: ClipItem[];
  intro: TimelineSegment;
  outro: TimelineSegment;
  logs: LogEntry[];
  transcription?: {
    language: string;
    probability: number;
    segments: TranscriptSegment[];
  };
  config: {
    language: string;
    model: string;
    device: string;
    computeType: string;
    minDuration: number;
    maxDuration: number;
    maxClips: number;
    subtitleMarginRatio: number;
  };
}
