import proxy from './proxy';
import type { 
  GameMode, 
  ShortcutMode, 
  Wnd,
  ScriptExecutionStatus,
  ScriptExecutionRequest,
  ScriptExecutionResponse,
  ParseScriptResponse,
  ValidateScriptResponse,
  TestScriptResponse
} from '../types';
import { type ShortcutModel } from '@src/components/content/shortcut/Content';

type ScriptType = 'collab' | 'activity';
type ShortcutConfig = {
  mode?: ShortcutMode;
  quickSell?: boolean;
};

export interface API {
  getFileList: (type: ScriptType) => Promise<{ files: string[] }>;
  readFile: (file: string, type: ScriptType) => Promise<string>;
  healthCheck: () => Promise<{ status: string }>;
  getGameWindows: () => Promise<{ windows: Array<Wnd> }>;
  getToolWindows: () => Promise<{ windows: Array<Wnd> }>;
  startAction: (config: {
    pid: number;
    action: string;
  }) => Promise<{ status: string }>;
  saveFile: (
    file: string,
    content: string,
    type: ScriptType
  ) => Promise<{ status: string }>;
  deleteFile: (file: string, type: ScriptType) => Promise<{ status: string }>;
  locateWindow: (pid: number) => Promise<{ status: string }>;
  getShortcut: () => Promise<{ shortcut: ShortcutModel }>;
  saveShortcut: (shortcut: ShortcutModel) => Promise<{ status: string }>;
  setShortcutConfig: (config: ShortcutConfig) => Promise<{ status: string }>;
  monitorShortcut: (value: boolean) => Promise<{ status: string }>;
  lockWindow: (config: {
    lock: boolean;
    pid?: number;
  }) => Promise<{ status: string }>;
  startAutoGame: (config: {
    main: { game: number; tool: number };
    sub: { game: number; tool: number };
    mode: GameMode;
    iceOnlySupport?: boolean;
  }) => Promise<{ status: string }>;
  startAutoBattle: (config: {
    main: { game: number; tool: number };
    sub: { game: number; tool: number };
  }) => Promise<{ status: string }>;
  isInGame: (config: {
    main: number;
    sub: number;
  }) => Promise<{ status: boolean }>;
  locateAutoWindow: (config: {game: number; tool: number; idx: 0 | 1}) => Promise<{ status: string }>;
  turnOffPC: () => Promise<{ status: string }>;
  captureScreenshot: (pid: number) => Promise<{ success: boolean; image: string; file_path: string; filename: string; message: string }>;
  test: () => Promise<{ status: string }>;
  parseScript: (content: string, name?: string, scriptType?: ScriptType) => Promise<ParseScriptResponse>;
  validateScript: (content: string) => Promise<ValidateScriptResponse>;
  testScript: (content: string, name?: string, scriptType?: ScriptType, dryRunOptions?: { dryRun?: boolean; sessionId?: string; actionDelayMs?: number; levelDelayMs?: number }) => Promise<TestScriptResponse>;
  executeScript: (request: ScriptExecutionRequest) => Promise<ScriptExecutionResponse>;
  getScriptStatus: (windowPid: number) => Promise<{ success: boolean; status: ScriptExecutionStatus }>;
  getModelStatus: () => Promise<{ model_version: string | null; trained_cards: string[]; total_samples: number; last_updated?: string }>;
  trainModel: () => Promise<{ success: boolean; model_version: string; train_samples: number }>;
  labelCrop: (cropId: string, cardName: string, cropMargins?: { top: number; bottom: number; left: number; right: number }) => Promise<{ success: boolean; message: string; new_model_version: string; dataset_stats: { labeled_count: number; unlabeled_count: number; per_card_counts: Record<string, number> } }>;
  getUnlabeledCrops: (limit?: number) => Promise<{ crops: Array<{ crop_id: string; image_base64: string; slot_idx: number; top_guesses: string[] }>; total_unlabeled: number }>;
  detectCards: (pid: number) => Promise<{ success: boolean; slots: Array<{ slot_idx: number; card: string; confidence: number; bbox: [number, number, number, number]; crop_id?: string; top_k_guesses?: string[] }>; model_version: string | null }>;
  batchTrainFromScreenshots: () => Promise<{ processed_count: number; cards_extracted: number; new_model_version: string; message: string }>;
  exportModel: (exportPath: string) => Promise<{ success: boolean; export_path: string; model_version: string }>;
  importModel: (importPath: string) => Promise<{ success: boolean; model_version: string; trained_cards: string[]; total_samples: number }>;
  getCardNames: () => Promise<{ cards: string[]; count: number }>;
}

export const api: API = {
  getFileList: async (type: 'collab' | 'activity') => {
    return await proxy.get(`get-file-list?type=${type}`);
  },
  readFile: async (file: string, type: ScriptType) => {
    // encode file name
    file = encodeURIComponent(file);
    return await proxy.post('read-file', { file, type });
  },
  healthCheck: async () => {
    return await proxy.get('health');
  },
  getGameWindows: async () => {
    return await proxy.get('game-windows');
  },
  getToolWindows: async () => {
    return await proxy.get('tool-windows');
  },
  startAction: async (config) => {
    return await proxy.post('start-action', config);
  },
  saveFile: async (file: string, content: string, type: ScriptType) => {
    return await proxy.post('save-file', { file, content, type });
  },
  deleteFile: async (file: string, type: ScriptType) => {
    return await proxy.post('delete-file', { file, type });
  },
  locateWindow: async (pid: number) => {
    return await proxy.post('locate-window', { pid });
  },
  getShortcut: async () => {
    return await proxy.get('shortcut');
  },
  saveShortcut: async (shortcut: ShortcutModel) => {
    return await proxy.post('shortcut', { shortcut });
  },
  setShortcutConfig: async (config: ShortcutConfig) => {
    return await proxy.post('shortcut-config', { config });
  },
  monitorShortcut: async (status: boolean) => {
    return await proxy.post('monitor-shortcut', { status });
  },
  lockWindow: async (config) => {
    return await proxy.post('lock-window', config);
  },
  startAutoGame: async (config) => {
    return await proxy.post('start-auto-game', config);
  },
  startAutoBattle: async (config) => {
    return await proxy.post('start-auto-battle', config);
  },
  isInGame: async (config) => {
    return await proxy.post('is-in-game', config);
  },
  locateAutoWindow: async (config) => {
    return await proxy.post('locate-auto-window', config);
  },
  turnOffPC: async () => {
    return await proxy.post('turn-off-pc');
  },
  captureScreenshot: async (pid: number) => {
    return await proxy.post('screenshot', { pid });
  },
  test: async () => {
    return await proxy.get('test-api');
  },
  parseScript: async (content: string, name?: string, scriptType?: ScriptType) => {
    return await proxy.post('script/parse', { content, name, script_type: scriptType });
  },
  validateScript: async (content: string) => {
    return await proxy.post('script/validate', { content });
  },
  testScript: async (content: string, name?: string, scriptType?: ScriptType, dryRunOptions?: { dryRun?: boolean; sessionId?: string; actionDelayMs?: number; levelDelayMs?: number }) => {
    return await proxy.post('script/test', {
      content,
      name,
      script_type: scriptType,
      dry_run: dryRunOptions?.dryRun ?? false,
      session_id: dryRunOptions?.sessionId ?? 'dry-run',
      action_delay_ms: dryRunOptions?.actionDelayMs ?? 300,
      level_delay_ms: dryRunOptions?.levelDelayMs ?? 500
    });
  },
  executeScript: async (request: ScriptExecutionRequest) => {
    return await proxy.post('script/execute', request);
  },
  getScriptStatus: async (windowPid: number) => {
    return await proxy.get(`script/status/${windowPid}`);
  },
  detectCards: async (pid: number) => {
    return await proxy.post('cards/detect', { window_pid: pid });
  },
  getUnlabeledCrops: async (limit: number = 10) => {
    return await proxy.get(`cards/unlabeled?limit=${limit}`);
  },
  labelCrop: async (cropId: string, cardName: string, cropMargins?: { top: number; bottom: number; left: number; right: number }) => {
    return await proxy.post('cards/label', { crop_id: cropId, card_name: cardName, crop_margins: cropMargins });
  },
  trainModel: async () => {
    return await proxy.post('cards/train');
  },
  getModelStatus: async () => {
    return await proxy.get('cards/model/status');
  },
  batchTrainFromScreenshots: async () => {
    return await proxy.post('cards/batch_train');
  },
  exportModel: async (exportPath: string) => {
    return await proxy.post('cards/export', { export_path: exportPath });
  },
  importModel: async (importPath: string) => {
    return await proxy.post('cards/import', { import_path: importPath });
  },
  getCardNames: async () => {
    return await proxy.get('cards/names');
  },
};
