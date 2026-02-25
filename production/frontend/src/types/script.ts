export interface ScriptExecutionStatus {
  state: 'idle' | 'running' | 'paused' | 'stopped' | 'error';
  current_level: number;
  current_second: number;
  last_executed_level?: number;
  last_event?: string;
  error_message?: string;
  actions_executed: number;
  start_time?: number;
}

export interface ScriptExecutionRequest {
  script_name: string;
  script_type: 'collab' | 'activity';
  window_pid: number;
  action: 'start' | 'pause' | 'resume' | 'stop';
}

export interface ScriptExecutionResponse {
  success: boolean;
  message: string;
  status?: ScriptExecutionStatus;
}

export interface ParseScriptResponse {
  success: boolean;
  script?: any;
  errors: string[];
  warnings: string[];
}

export interface ValidateScriptResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface SimulatedActionLog {
  level: number;
  second: number | null;
  action_type: string;
  description: string;
  details: Record<string, unknown>;
}

export interface TestScriptSummary {
  script_name: string;
  script_type: string;
  total_actions: number;
  levels_covered: number[];
  level_count: number;
  event_count: number;
  action_type_counts: Record<string, number>;
  cards_used: string[];
  deck: string[];
}

export interface TestScriptResponse {
  success: boolean;
  action_log: SimulatedActionLog[];
  vehicle_history: VehicleHistoryEntry[];  // For dry-run mode
  errors: string[];
  warnings: string[];
  summary: TestScriptSummary | null;
}

export interface VehicleHistoryEntry {
  event: 'level_change' | 'action';
  level: number;
  action?: SimulatedActionLog;
  state: VehicleState;
}

export interface VehicleState {
  side: 'left' | 'right';
  equipment: string | null;
  level: number;
  info: Record<number, { card: string | null; level: number | null }>;
}
