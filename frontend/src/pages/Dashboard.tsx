import React, { useState, useEffect } from 'react';
import { Pause, Square, Activity, Zap, Brain } from 'lucide-react';
import { useEvolutionStore } from '../stores/evolutionStore';
import { useEvolutionWebSocket } from '../hooks/useWebSocket';
import EvolutionControl from '../components/EvolutionControl';
import EvolutionChart from '../components/EvolutionChart';
import ConsciousnessPanel from '../components/ConsciousnessPanel';
import StatsCards from '../components/StatsCards';
import RecentActivity from '../components/RecentActivity';

const Dashboard: React.FC = () => {
  const {
    status,
    stats,
    fetchStatus,
    fetchStats,
    updateStatus,
    updateStats,
    addGeneration
  } = useEvolutionStore();

  const [selectedTab, setSelectedTab] = useState<'overview' | 'evolution' | 'consciousness'>('overview');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // WebSocket连接
  const { isConnected, lastMessage } = useEvolutionWebSocket();

  // 初始化数据
  useEffect(() => {
    fetchStatus();
    fetchStats();
  }, [fetchStatus, fetchStats]);

  // 自动刷新 - 只在WebSocket未连接时启用
  useEffect(() => {
    if (!autoRefresh || isConnected) return;

    const interval = setInterval(() => {
      fetchStatus();
      fetchStats();
    }, 10000); // 每10秒刷新一次（降低频率）

    return () => clearInterval(interval);
  }, [autoRefresh, isConnected, fetchStatus, fetchStats]);

  // 处理WebSocket消息
  useEffect(() => {
    if (lastMessage) {
      console.log('收到WebSocket消息:', lastMessage);
      try {
        // 根据消息类型更新状态
        switch (lastMessage.type) {
          case 'status_update':
            if (lastMessage.data) {
              updateStatus(lastMessage.data);
            }
            break;
          case 'stats_update':
            if (lastMessage.data) {
              updateStats(lastMessage.data);
            }
            break;
          case 'generation_complete':
            if (lastMessage.data) {
              addGeneration(lastMessage.data);
              // 代数完成时只更新统计信息
              fetchStats();
            }
            break;
          case 'evolution_update':
            // 通用更新，只在必要时重新获取数据
            if (lastMessage.data?.status_changed) {
              fetchStatus();
            }
            if (lastMessage.data?.stats_changed) {
              fetchStats();
            }
            break;
          default:
            console.log('未知的WebSocket消息类型:', lastMessage.type);
        }
      } catch (error) {
        console.error('处理WebSocket消息时出错:', error);
      }
    }
  }, [lastMessage, fetchStatus, fetchStats, updateStatus, updateStats, addGeneration]);



  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'text-green-400';
      case 'paused':
        return 'text-yellow-400';
      case 'stopped':
        return 'text-red-400';
      case 'idle':
      default:
        return 'text-gray-400';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Activity className="w-4 h-4 animate-pulse" />;
      case 'paused':
        return <Pause className="w-4 h-4" />;
      case 'stopped':
        return <Square className="w-4 h-4" />;
      case 'idle':
      default:
        return <Brain className="w-4 h-4" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 状态栏 */}
      <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4 mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className={`flex items-center space-x-2 ${getStatusColor()}`}>
              {getStatusIcon()}
              <span className={`text-sm font-medium ${getStatusColor()}`}>
                {status === 'running' ? '进化中' :
                 status === 'paused' ? '已暂停' : '空闲'}
              </span>
            </div>
            <div className="h-6 w-px bg-purple-500/30" />
            <div className="flex items-center space-x-2 text-sm text-gray-300">
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-400' : 'bg-red-400'
              }`} />
              <span>{isConnected ? 'WebSocket已连接' : 'WebSocket未连接'}</span>
            </div>
          </div>
          
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              autoRefresh 
                ? 'bg-purple-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            自动刷新
          </button>
        </div>
      </div>
        {/* 标签页导航 */}
        <div className="flex space-x-1 mb-8">
          {[
            { id: 'overview', label: '总览', icon: Activity },
            { id: 'evolution', label: '进化控制', icon: Zap },
            { id: 'consciousness', label: '意识状态', icon: Brain }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setSelectedTab(id as any)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all ${
                selectedTab === id
                  ? 'bg-purple-600 text-white shadow-lg'
                  : 'text-gray-300 hover:text-white hover:bg-white/10'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </div>

        {/* 标签页内容 */}
        {selectedTab === 'overview' && (
          <div className="space-y-8">
            {/* 统计卡片 */}
            <StatsCards stats={stats} />
            
            {/* 图表和活动 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-purple-400" />
                  进化趋势
                </h3>
                {stats && <EvolutionChart type="fitness" stats={stats} />}
              </div>
              
              <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-purple-400" />
                  最近活动
                </h3>
                <RecentActivity />
              </div>
            </div>
          </div>
        )}

        {selectedTab === 'evolution' && (
          <div className="space-y-8">
            {/* 进化控制面板 */}
            <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
              <h3 className="text-lg font-semibold text-white mb-6 flex items-center">
                <Zap className="w-5 h-5 mr-2 text-purple-400" />
                进化控制
              </h3>
              <EvolutionControl />
            </div>
            
            {/* 当前状态详情 */}
            <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">当前状态</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-black/20 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-1">当前代数</div>
                  <div className="text-2xl font-bold text-white">
                    {stats?.current_generation || 0}
                  </div>
                </div>
                <div className="bg-black/20 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-1">运行状态</div>
                  <div className={`text-2xl font-bold ${getStatusColor()}`}>
                    {status || 'idle'}
                  </div>
                </div>
                <div className="bg-black/20 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-1">最佳适应度</div>
                  <div className="text-2xl font-bold text-green-400">
                    {stats?.best_fitness_ever?.toFixed(2) || '0.00'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedTab === 'consciousness' && (
          <div className="space-y-8">
            {/* 意识状态面板 */}
            <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
              <h3 className="text-lg font-semibold text-white mb-6 flex items-center">
                <Brain className="w-5 h-5 mr-2 text-purple-400" />
                意识状态监控
              </h3>
              <ConsciousnessPanel consciousness={null} />
            </div>
          </div>
        )}
    </div>
  );
};

export default Dashboard;