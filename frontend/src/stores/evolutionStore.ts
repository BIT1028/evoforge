import { create } from 'zustand';
import { evolutionApi } from '../services/api';
import { 
  EvolutionConfig, 
  EvolutionStatus, 
  EvolutionStats, 
  Generation, 
  DigitalCell 
} from '../types/evolution';

interface EvolutionStore {
  // 状态
  status: EvolutionStatus | null;
  stats: EvolutionStats | null;
  generations: Generation[];
  bestCells: DigitalCell[];
  isLoading: boolean;
  error: string | null;
  config: EvolutionConfig | null;
  
  // 操作
  fetchStatus: () => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchGenerations: (limit?: number, offset?: number) => Promise<void>;
  fetchBestCells: (limit?: number) => Promise<void>;
  
  startEvolution: (config: EvolutionConfig) => Promise<void>;
  stopEvolution: () => Promise<void>;
  pauseEvolution: () => Promise<void>;
  resumeEvolution: () => Promise<void>;
  resetEvolution: () => Promise<void>;
  
  // 实时更新
  updateStatus: (status: EvolutionStatus) => void;
  updateStats: (stats: EvolutionStats) => void;
  addGeneration: (generation: Generation) => void;
  
  // 错误处理
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // 配置管理
  updateConfig: (config: EvolutionConfig) => void;
}

export const useEvolutionStore = create<EvolutionStore>((set, get) => ({
  // 初始状态
  status: null,
  stats: null,
  generations: [],
  bestCells: [],
  isLoading: false,
  error: null,
  config: null,
  
  // 获取进化状态
  fetchStatus: async () => {
    try {
      set({ isLoading: true, error: null });
      const status = await evolutionApi.getStatus();
      set({ status, isLoading: false });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取状态失败';
      set({ error: errorMessage, isLoading: false });
    }
  },
  
  // 获取统计信息
  fetchStats: async () => {
    try {
      set({ error: null });
      const stats = await evolutionApi.getStats();
      set({ stats });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取统计失败';
      set({ error: errorMessage });
    }
  },
  
  // 获取代数列表
  fetchGenerations: async (limit = 20, offset = 0) => {
    try {
      set({ error: null });
      const generations = await evolutionApi.getGenerations(limit, offset);
      set({ generations });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取代数失败';
      set({ error: errorMessage });
    }
  },
  
  // 获取最佳细胞
  fetchBestCells: async (limit = 10) => {
    try {
      set({ error: null });
      const bestCells = await evolutionApi.getBestCells(limit);
      set({ bestCells });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取最佳细胞失败';
      set({ error: errorMessage });
    }
  },
  
  // 启动进化
  startEvolution: async (config: EvolutionConfig) => {
    try {
      set({ isLoading: true, error: null });
      const status = await evolutionApi.startEvolution(config);
      set({ status, isLoading: false });
      
      // 启动后刷新统计信息
      setTimeout(() => {
        get().fetchStats();
      }, 1000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '启动进化失败';
      set({ error: errorMessage, isLoading: false });
    }
  },
  
  // 停止进化
  stopEvolution: async () => {
    try {
      set({ isLoading: true, error: null });
      const status = await evolutionApi.stopEvolution();
      set({ status, isLoading: false });
      
      // 停止后刷新统计信息
      setTimeout(() => {
        get().fetchStats();
      }, 1000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '停止进化失败';
      set({ error: errorMessage, isLoading: false });
    }
  },
  
  // 暂停进化
  pauseEvolution: async () => {
    try {
      set({ isLoading: true, error: null });
      const status = await evolutionApi.pauseEvolution();
      set({ status, isLoading: false });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '暂停进化失败';
      set({ error: errorMessage, isLoading: false });
    }
  },
  
  // 恢复进化
  resumeEvolution: async () => {
    try {
      set({ isLoading: true, error: null });
      const status = await evolutionApi.resumeEvolution();
      set({ status, isLoading: false });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '恢复进化失败';
      set({ error: errorMessage, isLoading: false });
    }
  },
  
  // 重置进化
  resetEvolution: async () => {
    try {
      set({ isLoading: true, error: null });
      const status = await evolutionApi.resetEvolution();
      set({ 
        status, 
        isLoading: false,
        generations: [],
        bestCells: [],
        stats: null
      });
      
      // 重置后刷新统计信息
      setTimeout(() => {
        get().fetchStats();
      }, 1000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '重置进化失败';
      set({ error: errorMessage, isLoading: false });
    }
  },
  
  // 实时更新状态
  updateStatus: (status: EvolutionStatus) => {
    set({ status });
  },
  
  // 实时更新统计
  updateStats: (stats: EvolutionStats) => {
    set({ stats });
  },
  
  // 添加新代数
  addGeneration: (generation: Generation) => {
    set((state) => ({
      generations: [generation, ...state.generations].slice(0, 50) // 保持最近50代
    }));
  },
  
  // 设置错误
  setError: (error: string | null) => {
    set({ error });
  },
  
  // 清除错误
  clearError: () => {
    set({ error: null });
  },
  
  // 更新配置
  updateConfig: (config: EvolutionConfig) => {
    set({ config });
  }
}));

// 选择器函数
export const useEvolutionStatus = () => useEvolutionStore((state) => state.status);
export const useEvolutionStats = () => useEvolutionStore((state) => state.stats);
export const useEvolutionGenerations = () => useEvolutionStore((state) => state.generations);
export const useEvolutionBestCells = () => useEvolutionStore((state) => state.bestCells);
export const useEvolutionLoading = () => useEvolutionStore((state) => state.isLoading);
export const useEvolutionError = () => useEvolutionStore((state) => state.error);

// 计算属性
export const useEvolutionProgress = () => {
  return useEvolutionStore((state) => {
    if (!state.stats) return 0;
    
    // 假设最大代数为100，计算进度百分比
    const maxGenerations = 100;
    return Math.min((state.stats.current_generation / maxGenerations) * 100, 100);
  });
};

export const useEvolutionPerformance = () => {
  return useEvolutionStore((state) => {
    if (!state.generations || state.generations.length === 0) {
      return { trend: 'stable', improvement: 0 };
    }
    
    const recent = state.generations.slice(0, 5);
    if (recent.length < 2) {
      return { trend: 'stable', improvement: 0 };
    }
    
    const latest = recent[0].best_fitness;
    const previous = recent[recent.length - 1].best_fitness;
    const improvement = ((latest - previous) / previous) * 100;
    
    let trend: 'improving' | 'declining' | 'stable' = 'stable';
    if (improvement > 5) trend = 'improving';
    else if (improvement < -5) trend = 'declining';
    
    return { trend, improvement };
  });
};