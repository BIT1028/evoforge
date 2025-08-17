import React, { useState } from 'react';
import { Play, Pause, Square, RotateCcw, Settings, AlertCircle } from 'lucide-react';
import { useEvolutionStore } from '../stores/evolutionStore';
import { EvolutionConfig } from '../types/evolution';

interface EvolutionControlProps {
  className?: string;
}

const EvolutionControl: React.FC<EvolutionControlProps> = ({ className = '' }) => {
  const {
    status,
    config,
    isLoading,
    error,
    startEvolution,
    stopEvolution,
    pauseEvolution,
    resumeEvolution,
    resetEvolution,
    updateConfig
  } = useEvolutionStore();

  const [showConfig, setShowConfig] = useState(false);
  const [localConfig, setLocalConfig] = useState<EvolutionConfig>(config || {
    population_size: 100,
    max_generations: 1000,
    mutation_rate: 0.1,
    crossover_rate: 0.8,
    elite_rate: 0.1,
    selection_method: 'tournament' as const,
    tournament_size: 5,
    fitness_threshold: 0.95
  });

  // 处理开始进化
  const handleStart = async () => {
    try {
      await startEvolution(localConfig);
    } catch (error) {
      console.error('启动进化失败:', error);
    }
  };

  // 处理暂停进化
  const handlePause = async () => {
    try {
      await pauseEvolution();
    } catch (error) {
      console.error('暂停进化失败:', error);
    }
  };

  // 处理恢复进化
  const handleResume = async () => {
    try {
      await resumeEvolution();
    } catch (error) {
      console.error('恢复进化失败:', error);
    }
  };

  // 处理停止进化
  const handleStop = async () => {
    try {
      await stopEvolution();
    } catch (error) {
      console.error('停止进化失败:', error);
    }
  };

  // 处理重置进化
  const handleReset = async () => {
    if (window.confirm('确定要重置进化过程吗？这将清除所有历史数据。')) {
      try {
        await resetEvolution();
      } catch (error) {
        console.error('重置进化失败:', error);
      }
    }
  };

  // 处理配置更新
  const handleConfigUpdate = () => {
    updateConfig(localConfig);
    setShowConfig(false);
  };

  // 获取状态颜色
  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'text-green-600';
      case 'paused':
        return 'text-yellow-600';
      case 'stopped':
        return 'text-red-600';
      case 'idle':
      default:
        return 'text-gray-600';
    }
  };

  // 获取状态文本
  const getStatusText = () => {
    switch (status) {
      case 'running':
        return '运行中';
      case 'paused':
        return '已暂停';
      case 'stopped':
        return '已停止';
      case 'idle':
      default:
        return '空闲';
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      {/* 标题和状态 */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-800">进化控制</h2>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${
            status === 'running' ? 'bg-green-500 animate-pulse' :
            status === 'paused' ? 'bg-yellow-500' :
            status === 'stopped' ? 'bg-red-500' : 'bg-gray-400'
          }`}></div>
          <span className={`text-sm font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </span>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700 text-sm">{error}</span>
        </div>
      )}

      {/* 控制按钮 */}
      <div className="flex flex-wrap gap-3 mb-6">
        {/* 开始/恢复按钮 */}
        {(status === 'idle' || status === 'stopped') && (
          <button
            onClick={handleStart}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="w-4 h-4" />
            <span>开始进化</span>
          </button>
        )}

        {status === 'paused' && (
          <button
            onClick={handleResume}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="w-4 h-4" />
            <span>恢复进化</span>
          </button>
        )}

        {/* 暂停按钮 */}
        {status === 'running' && (
          <button
            onClick={handlePause}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Pause className="w-4 h-4" />
            <span>暂停进化</span>
          </button>
        )}

        {/* 停止按钮 */}
        {(status === 'running' || status === 'paused') && (
          <button
            onClick={handleStop}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Square className="w-4 h-4" />
            <span>停止进化</span>
          </button>
        )}

        {/* 重置按钮 */}
        <button
          onClick={handleReset}
          disabled={isLoading || status === 'running'}
          className="flex items-center space-x-2 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          <span>重置</span>
        </button>

        {/* 配置按钮 */}
        <button
          onClick={() => setShowConfig(!showConfig)}
          disabled={status === 'running'}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Settings className="w-4 h-4" />
          <span>配置</span>
        </button>
      </div>

      {/* 配置面板 */}
      {showConfig && (
        <div className="border-t pt-6">
          <h3 className="text-lg font-medium text-gray-800 mb-4">进化配置</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 种群大小 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                种群大小
              </label>
              <input
                type="number"
                min="10"
                max="1000"
                value={localConfig.population_size}
                onChange={(e) => setLocalConfig({
                  ...localConfig,
                  population_size: parseInt(e.target.value) || 50
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* 最大代数 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                最大代数
              </label>
              <input
                type="number"
                min="1"
                max="10000"
                value={localConfig.max_generations}
                onChange={(e) => setLocalConfig({
                  ...localConfig,
                  max_generations: parseInt(e.target.value) || 100
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* 变异率 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                变异率
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={localConfig.mutation_rate}
                onChange={(e) => setLocalConfig({
                  ...localConfig,
                  mutation_rate: parseFloat(e.target.value) || 0.1
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* 交叉率 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                交叉率
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={localConfig.crossover_rate}
                onChange={(e) => setLocalConfig({
                  ...localConfig,
                  crossover_rate: parseFloat(e.target.value) || 0.8
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* 精英保留率 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                精英保留率
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={localConfig.elite_rate}
                onChange={(e) => setLocalConfig({
                  ...localConfig,
                  elite_rate: parseFloat(e.target.value) || 0.1
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* 选择方法 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                选择方法
              </label>
              <select
                value={localConfig.selection_method}
                onChange={(e) => setLocalConfig({
                  ...localConfig,
                  selection_method: e.target.value as 'tournament' | 'roulette' | 'rank'
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="tournament">锦标赛选择</option>
                <option value="roulette">轮盘赌选择</option>
                <option value="rank">排名选择</option>
              </select>
            </div>
          </div>

          {/* 配置按钮 */}
          <div className="flex justify-end space-x-3 mt-6">
            <button
              onClick={() => {
                setLocalConfig(config || {
                  population_size: 100,
                  max_generations: 1000,
                  mutation_rate: 0.1,
                  crossover_rate: 0.8,
                  elite_rate: 0.1,
                  selection_method: 'tournament' as const,
                  tournament_size: 5,
                  fitness_threshold: 0.95
                });
                setShowConfig(false);
              }}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleConfigUpdate}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              保存配置
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default EvolutionControl;