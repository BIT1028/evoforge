import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { EvolutionConfig, EvolutionStatus, EvolutionStats, Generation, DigitalCell } from '../types/evolution';

// API基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    console.log(`API请求: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('请求拦截器错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(`API响应: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API错误:', error.response?.data || error.message);
    
    // 统一错误处理
    if (error.response?.status === 401) {
      // 处理未授权
      console.error('未授权访问');
    } else if (error.response?.status === 500) {
      // 处理服务器错误
      console.error('服务器内部错误');
    }
    
    return Promise.reject(error);
  }
);

// 进化API
export const evolutionApi = {
  // 获取进化状态
  async getStatus(): Promise<EvolutionStatus> {
    const response = await apiClient.get('/evolution/status');
    return response.data;
  },

  // 获取进化统计
  async getStats(): Promise<EvolutionStats> {
    const response = await apiClient.get('/evolution/stats');
    return response.data;
  },

  // 启动进化
  async startEvolution(config: EvolutionConfig): Promise<EvolutionStatus> {
    const response = await apiClient.post('/evolution/start', config);
    return response.data;
  },

  // 停止进化
  async stopEvolution(): Promise<EvolutionStatus> {
    const response = await apiClient.post('/evolution/stop');
    return response.data;
  },

  // 暂停进化
  async pauseEvolution(): Promise<EvolutionStatus> {
    const response = await apiClient.post('/evolution/pause');
    return response.data;
  },

  // 恢复进化
  async resumeEvolution(): Promise<EvolutionStatus> {
    const response = await apiClient.post('/evolution/resume');
    return response.data;
  },

  // 重置进化
  async resetEvolution(): Promise<EvolutionStatus> {
    const response = await apiClient.post('/evolution/reset');
    return response.data;
  },

  // 获取代数列表
  async getGenerations(limit = 20, offset = 0): Promise<Generation[]> {
    const response = await apiClient.get('/evolution/generations', {
      params: { limit, offset }
    });
    return response.data;
  },

  // 获取指定代数的细胞
  async getGenerationCells(generationId: number, limit = 50, offset = 0): Promise<DigitalCell[]> {
    const response = await apiClient.get(`/evolution/generations/${generationId}/cells`, {
      params: { limit, offset }
    });
    return response.data;
  },

  // 获取最佳细胞
  async getBestCells(limit = 10): Promise<DigitalCell[]> {
    const response = await apiClient.get('/evolution/cells/best', {
      params: { limit }
    });
    return response.data;
  },

  // 进化控制
  async evolutionControl(action: string, config?: any): Promise<EvolutionStatus> {
    const response = await apiClient.post('/evolution/control', {
      action,
      config
    });
    return response.data;
  },

  // 获取意识状态
  async getConsciousnessState(): Promise<any> {
    const response = await apiClient.get('/evolution/consciousness');
    return response.data;
  }
};

// 任务API
export interface Task {
  id: number;
  name: string;
  description: string;
  priority: number;
  category: string;
  template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  name: string;
  description: string;
  priority: number;
  category: string;
  template: string;
  is_active: boolean;
}

export interface TaskUpdate {
  name?: string;
  description?: string;
  priority?: number;
  category?: string;
  template?: string;
  is_active?: boolean;
}

export const tasksApi = {
  // 获取任务列表
  async getTasks(params?: {
    skip?: number;
    limit?: number;
    category?: string;
    is_active?: boolean;
    search?: string;
  }): Promise<Task[]> {
    const response = await apiClient.get('/tasks/', { params });
    return response.data;
  },

  // 获取单个任务
  async getTask(taskId: number): Promise<Task> {
    const response = await apiClient.get(`/tasks/${taskId}`);
    return response.data;
  },

  // 创建任务
  async createTask(task: TaskCreate): Promise<Task> {
    const response = await apiClient.post('/tasks/', task);
    return response.data;
  },

  // 更新任务
  async updateTask(taskId: number, task: TaskUpdate): Promise<Task> {
    const response = await apiClient.put(`/tasks/${taskId}`, task);
    return response.data;
  },

  // 删除任务
  async deleteTask(taskId: number): Promise<void> {
    await apiClient.delete(`/tasks/${taskId}`);
  },

  // 切换任务状态
  async toggleTaskStatus(taskId: number): Promise<{ message: string; is_active: boolean }> {
    const response = await apiClient.post(`/tasks/${taskId}/toggle`);
    return response.data;
  },

  // 获取任务分类
  async getTaskCategories(): Promise<string[]> {
    const response = await apiClient.get('/tasks/categories/');
    return response.data;
  },

  // 获取任务统计
  async getTaskStats(): Promise<any> {
    const response = await apiClient.get('/tasks/stats/');
    return response.data;
  },

  // 批量操作
  async batchOperation(operation: string, taskIds: number[], options?: any): Promise<any> {
    const response = await apiClient.post('/tasks/batch', {
      operation,
      task_ids: taskIds,
      ...options
    });
    return response.data;
  }
};

// 评估API
export interface EvaluationLog {
  id: number;
  digital_cell_id: number;
  task_id?: number;
  oracle_request: string;
  oracle_response: string;
  fitness_score: number;
  api_cost: number;
  execution_time: number;
  created_at: string;
}

export interface ApiCost {
  id: number;
  service_name: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  created_at: string;
}

export const evaluationApi = {
  // 甲骨文评估
  async evaluateWithOracle(request: {
    code: string;
    task_description: string;
    cell_id?: number;
    task_id?: number;
  }): Promise<any> {
    const response = await apiClient.post('/evaluation/oracle', request);
    return response.data;
  },

  // 执行代码
  async executeCode(code: string, testInput = '', useDocker = true): Promise<any> {
    const response = await apiClient.post('/evaluation/execute', {
      code,
      test_input: testInput,
      use_docker: useDocker
    });
    return response.data;
  },

  // 验证代码语法
  async validateCodeSyntax(code: string): Promise<any> {
    const response = await apiClient.post('/evaluation/validate', { code });
    return response.data;
  },

  // 获取评估日志
  async getEvaluationLogs(params?: {
    skip?: number;
    limit?: number;
    cell_id?: number;
    task_id?: number;
    min_fitness?: number;
    max_fitness?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<EvaluationLog[]> {
    const response = await apiClient.get('/evaluation/logs', { params });
    return response.data;
  },

  // 获取API成本
  async getApiCosts(params?: {
    skip?: number;
    limit?: number;
    service_name?: string;
    model_name?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<ApiCost[]> {
    const response = await apiClient.get('/evaluation/costs', { params });
    return response.data;
  },

  // 获取评估统计
  async getEvaluationStats(days = 7): Promise<any> {
    const response = await apiClient.get('/evaluation/stats', {
      params: { days }
    });
    return response.data;
  },

  // 获取性能指标
  async getPerformanceMetrics(hours = 24): Promise<any> {
    const response = await apiClient.get('/evaluation/performance', {
      params: { hours }
    });
    return response.data;
  },

  // 删除评估日志
  async deleteEvaluationLog(logId: number): Promise<void> {
    await apiClient.delete(`/evaluation/logs/${logId}`);
  }
};

// 健康检查API
export const healthApi = {
  // 检查API健康状态
  async checkHealth(): Promise<{ status: string; timestamp: string }> {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // 获取系统信息
  async getSystemInfo(): Promise<any> {
    const response = await apiClient.get('/system/info');
    return response.data;
  }
};

// 导出默认API客户端
export default apiClient;

// 工具函数
export const formatApiError = (error: any): string => {
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.message) {
    return error.message;
  }
  return '未知错误';
};

// 重试机制
export const withRetry = async <T>(
  apiCall: () => Promise<T>,
  maxRetries = 3,
  delay = 1000
): Promise<T> => {
  let lastError: any;
  
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await apiCall();
    } catch (error) {
      lastError = error;
      
      if (i === maxRetries) {
        break;
      }
      
      // 指数退避
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
    }
  }
  
  throw lastError;
};