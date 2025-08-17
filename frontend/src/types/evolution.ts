// 进化配置
export interface EvolutionConfig {
  population_size: number;
  max_generations: number;
  mutation_rate: number;
  crossover_rate: number;
  elite_rate: number;
  selection_method: 'tournament' | 'roulette' | 'rank';
  tournament_size?: number;
  fitness_threshold?: number;
  stagnation_limit?: number;
  diversity_threshold?: number;
}

// 进化状态
export type EvolutionStatus = 'idle' | 'running' | 'paused' | 'stopped' | 'completed' | 'error';

// 数字细胞
export interface DigitalCell {
  id: string;
  generation_id: string;
  gene_sequence: string;
  generated_code: string;
  fitness_score: number;
  parent_id?: string;
  mutation_rate: number;
  created_at: string;
  updated_at: string;
}

// 代数信息
export interface Generation {
  id: string;
  generation_number: number;
  population_size: number;
  average_fitness: number;
  best_fitness: number;
  worst_fitness: number;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  cells?: DigitalCell[];
}

// 进化统计
export interface EvolutionStats {
  current_generation: number;
  total_generations: number;
  total_cells: number;
  best_fitness_ever: number;
  average_fitness_trend: number[];
  best_fitness_trend: number[];
  diversity_trend: number[];
  stagnation_count: number;
  runtime_seconds: number;
  cells_per_second: number;
  api_calls_total: number;
  api_cost_total: number;
}

// 进化控制请求
export interface EvolutionControlRequest {
  action: 'start' | 'stop' | 'pause' | 'resume' | 'reset';
  config?: EvolutionConfig;
}

// 意识状态
export interface ConsciousnessState {
  is_active: boolean;
  current_focus: string;
  reflection_depth: number;
  awareness_level: number;
  last_reflection: string;
  insights: string[];
  concerns: string[];
  suggestions: string[];
  emotional_state: 'curious' | 'focused' | 'concerned' | 'excited' | 'contemplative';
  updated_at: string;
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

// 进化事件类型
export type EvolutionEventType = 
  | 'evolution_started'
  | 'evolution_stopped'
  | 'evolution_paused'
  | 'evolution_resumed'
  | 'evolution_reset'
  | 'generation_completed'
  | 'cell_evaluated'
  | 'fitness_improved'
  | 'consciousness_updated'
  | 'error_occurred';

// 进化事件数据
export interface EvolutionEvent {
  type: EvolutionEventType;
  data: {
    generation?: Generation;
    cell?: DigitalCell;
    stats?: EvolutionStats;
    consciousness?: ConsciousnessState;
    error?: string;
    message?: string;
  };
  timestamp: string;
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// 错误类型
export interface ApiError {
  code: string;
  message: string;
  details?: any;
}

// 性能指标
export interface PerformanceMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: number;
  active_connections: number;
  request_rate: number;
  error_rate: number;
  response_time: number;
}

// 系统健康状态
export interface SystemHealth {
  status: 'healthy' | 'warning' | 'critical';
  services: {
    database: 'up' | 'down' | 'degraded';
    redis: 'up' | 'down' | 'degraded';
    websocket: 'up' | 'down' | 'degraded';
    oracle: 'up' | 'down' | 'degraded';
    executor: 'up' | 'down' | 'degraded';
  };
  metrics: PerformanceMetrics;
  last_check: string;
}