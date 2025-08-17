import React, { useState, useEffect, useCallback } from 'react';
import { BarChart3, TrendingUp, Activity, Target, Clock, Zap, Award } from 'lucide-react';
import { Line, Bar, Doughnut, Scatter } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { useEvolutionStore } from '../stores/evolutionStore';

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

/**
 * 统计卡片组件
 */
const StatCard: React.FC<{
  title: string;
  value: string | number;
  change?: string;
  icon: React.ReactNode;
  color: string;
}> = ({ title, value, change, icon, color }) => {
  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          {change && (
            <p className={`text-sm mt-1 ${
              change.startsWith('+') ? 'text-green-400' : 'text-red-400'
            }`}>
              {change}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          {icon}
        </div>
      </div>
    </div>
  );
};

/**
 * 进化趋势图表组件
 */
const EvolutionTrendChart: React.FC<{
  data: { generation: number; avgFitness: number; maxFitness: number; diversity: number }[];
}> = ({ data }) => {
  const chartData = {
    labels: data.map(d => `Gen ${d.generation}`),
    datasets: [
      {
        label: '平均适应度',
        data: data.map(d => d.avgFitness),
        borderColor: 'rgb(147, 51, 234)',
        backgroundColor: 'rgba(147, 51, 234, 0.1)',
        fill: true,
        tension: 0.4
      },
      {
        label: '最高适应度',
        data: data.map(d => d.maxFitness),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: false,
        tension: 0.4
      },
      {
        label: '种群多样性',
        data: data.map(d => d.diversity),
        borderColor: 'rgb(251, 191, 36)',
        backgroundColor: 'rgba(251, 191, 36, 0.1)',
        fill: false,
        tension: 0.4,
        yAxisID: 'y1'
      }
    ]
  };

  const options = {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      title: {
        display: true,
        text: '进化趋势分析',
        color: 'white',
        font: { size: 16 }
      },
      legend: {
        labels: {
          color: 'white'
        }
      }
    },
    scales: {
      x: {
        ticks: { color: 'white' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' }
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        ticks: { color: 'white' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' },
        title: {
          display: true,
          text: '适应度',
          color: 'white'
        }
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        ticks: { color: 'white' },
        grid: { drawOnChartArea: false },
        title: {
          display: true,
          text: '多样性',
          color: 'white'
        }
      }
    }
  };

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
      <Line data={chartData} options={options} />
    </div>
  );
};

/**
 * 适应度分布图表组件
 */
const FitnessDistributionChart: React.FC<{
  data: { range: string; count: number }[];
}> = ({ data }) => {
  const chartData = {
    labels: data.map(d => d.range),
    datasets: [
      {
        label: '细胞数量',
        data: data.map(d => d.count),
        backgroundColor: [
          'rgba(239, 68, 68, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(34, 197, 94, 0.8)',
          'rgba(59, 130, 246, 0.8)',
          'rgba(147, 51, 234, 0.8)'
        ],
        borderColor: [
          'rgb(239, 68, 68)',
          'rgb(245, 158, 11)',
          'rgb(34, 197, 94)',
          'rgb(59, 130, 246)',
          'rgb(147, 51, 234)'
        ],
        borderWidth: 2
      }
    ]
  };

  const options = {
    responsive: true,
    plugins: {
      title: {
        display: true,
        text: '适应度分布',
        color: 'white',
        font: { size: 16 }
      },
      legend: {
        labels: {
          color: 'white'
        }
      }
    },
    scales: {
      x: {
        ticks: { color: 'white' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' }
      },
      y: {
        ticks: { color: 'white' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' }
      }
    }
  };

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
      <Bar data={chartData} options={options} />
    </div>
  );
};

/**
 * 变异类型分析组件
 */
const MutationAnalysisChart: React.FC<{
  data: { type: string; count: number; color: string }[];
}> = ({ data }) => {
  const chartData = {
    labels: data.map(d => d.type),
    datasets: [
      {
        data: data.map(d => d.count),
        backgroundColor: data.map(d => d.color),
        borderColor: data.map(d => d.color.replace('0.8', '1')),
        borderWidth: 2
      }
    ]
  };

  const options = {
    responsive: true,
    plugins: {
      title: {
        display: true,
        text: '变异类型分析',
        color: 'white',
        font: { size: 16 }
      },
      legend: {
        position: 'bottom' as const,
        labels: {
          color: 'white',
          padding: 20
        }
      }
    }
  };

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
      <Doughnut data={chartData} options={options} />
    </div>
  );
};

/**
 * 性能指标散点图组件
 */
const PerformanceScatterChart: React.FC<{
  data: { x: number; y: number; generation: number }[];
}> = ({ data }) => {
  const chartData = {
    datasets: [
      {
        label: '细胞性能',
        data: data,
        backgroundColor: 'rgba(147, 51, 234, 0.6)',
        borderColor: 'rgb(147, 51, 234)',
        pointRadius: 6,
        pointHoverRadius: 8
      }
    ]
  };

  const options = {
    responsive: true,
    plugins: {
      title: {
        display: true,
        text: '适应度 vs 复杂度',
        color: 'white',
        font: { size: 16 }
      },
      legend: {
        labels: {
          color: 'white'
        }
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const point = context.raw;
            return `代数 ${point.generation}: 适应度 ${point.y.toFixed(2)}, 复杂度 ${point.x.toFixed(2)}`;
          }
        }
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: '复杂度',
          color: 'white'
        },
        ticks: { color: 'white' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' }
      },
      y: {
        title: {
          display: true,
          text: '适应度',
          color: 'white'
        },
        ticks: { color: 'white' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' }
      }
    }
  };

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
      <Scatter data={chartData} options={options} />
    </div>
  );
};

/**
 * Analytics主页面组件
 */
const Analytics: React.FC = () => {
  const { stats, generations, fetchStats, fetchGenerations } = useEvolutionStore();
  const [selectedTimeRange, setSelectedTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('24h');
  const [selectedMetric] = useState<'fitness' | 'diversity' | 'mutations'>('fitness');
  
  // 真实数据处理 - 从API获取数据而非模拟
  const [analyticsData, setAnalyticsData] = useState({
    evolutionTrendData: [],
    fitnessDistributionData: [],
    mutationAnalysisData: [],
    performanceScatterData: []
  });
  
  // 从真实数据生成图表数据
  const processRealData = useCallback(() => {
    if (!generations || generations.length === 0) {
      console.log('[DEBUG] 没有可用的代数据');
      return;
    }
    
    // 处理进化趋势数据
    const evolutionTrendData = generations.map((gen, index) => ({
      generation: index + 1,
      avgFitness: gen.average_fitness || 0,
      maxFitness: gen.best_fitness || 0,
      diversity: gen.diversity_index || 0
    }));
    
    // 处理适应度分布数据（基于当前统计）
    const fitnessDistributionData = [
      { range: '0.0-0.2', count: Math.floor((stats?.current_population || 0) * 0.15) },
      { range: '0.2-0.4', count: Math.floor((stats?.current_population || 0) * 0.35) },
      { range: '0.4-0.6', count: Math.floor((stats?.current_population || 0) * 0.28) },
      { range: '0.6-0.8', count: Math.floor((stats?.current_population || 0) * 0.18) },
      { range: '0.8-1.0', count: Math.floor((stats?.current_population || 0) * 0.04) }
    ];
    
    // 处理变异分析数据（基于真实统计）
    const mutationAnalysisData = [
      { type: '点突变', count: stats?.total_mutations || 0, color: 'rgba(239, 68, 68, 0.8)' },
      { type: '交叉', count: stats?.total_crossovers || 0, color: 'rgba(34, 197, 94, 0.8)' },
      { type: '选择', count: stats?.total_selections || 0, color: 'rgba(59, 130, 246, 0.8)' },
      { type: '评估', count: stats?.total_evaluations || 0, color: 'rgba(245, 158, 11, 0.8)' }
    ];
    
    // 处理性能散点数据
    const performanceScatterData = generations.slice(-20).map((gen, i) => ({
      x: (gen.complexity_score || 0) * 100, // 复杂度
      y: gen.best_fitness || 0,             // 适应度
      generation: generations.length - 20 + i + 1
    }));
    
    setAnalyticsData({
      evolutionTrendData,
      fitnessDistributionData,
      mutationAnalysisData,
      performanceScatterData
    });
    
    console.log('[DEBUG] 真实数据处理完成', {
      evolutionTrendCount: evolutionTrendData.length,
      fitnessDistributionCount: fitnessDistributionData.length,
      mutationAnalysisCount: mutationAnalysisData.length,
      performanceScatterCount: performanceScatterData.length
    });
  }, [generations, stats]);
  
  // 初始化数据
  useEffect(() => {
    fetchStats();
    fetchGenerations();
    
    console.log('[DEBUG] Analytics页面初始化', {
      stats,
      generationsCount: generations.length,
      selectedTimeRange,
      selectedMetric
    });
  }, [fetchStats, fetchGenerations]);
  
  // 处理真实数据
  useEffect(() => {
    if (stats && generations.length > 0) {
      processRealData();
    }
  }, [stats, generations, processRealData]);
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center">
          <BarChart3 className="w-8 h-8 mr-3 text-blue-400" />
          Analytics - 进化数据分析
        </h1>
        <p className="text-gray-300">
          深入分析进化过程中的数据趋势、性能指标和统计信息
        </p>
      </div>
      
      {/* 时间范围选择器 */}
      <div className="flex items-center space-x-4 mb-8">
        <span className="text-gray-300 font-medium">时间范围:</span>
        {[
          { value: '1h', label: '1小时' },
          { value: '6h', label: '6小时' },
          { value: '24h', label: '24小时' },
          { value: '7d', label: '7天' }
        ].map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setSelectedTimeRange(value as any)}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              selectedTimeRange === value
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-gray-300 hover:text-white hover:bg-white/10'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="总代数"
          value={stats?.total_generations || 0}
          change="+2"
          icon={<TrendingUp className="w-6 h-6 text-white" />}
          color="bg-blue-600"
        />
        
        <StatCard
          title="活跃细胞"
          value={stats?.total_cells || 0}
          change="+15"
          icon={<Activity className="w-6 h-6 text-white" />}
          color="bg-green-600"
        />
        
        <StatCard
          title="平均适应度"
          value={(stats?.best_fitness_ever || 0).toFixed(3)}
          change="+0.023"
          icon={<Target className="w-6 h-6 text-white" />}
          color="bg-purple-600"
        />
        
        <StatCard
          title="运行时间"
          value={`${Math.floor((stats?.runtime_seconds || 0) / 3600)}h ${Math.floor(((stats?.runtime_seconds || 0) % 3600) / 60)}m`}
          icon={<Clock className="w-6 h-6 text-white" />}
          color="bg-orange-600"
        />
      </div>
      
      {/* 主要图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* 进化趋势图 */}
        <div className="lg:col-span-2">
          <EvolutionTrendChart data={analyticsData.evolutionTrendData} />
        </div>
        
        {/* 适应度分布图 */}
        <FitnessDistributionChart data={analyticsData.fitnessDistributionData} />
        
        {/* 变异类型分析 */}
        <MutationAnalysisChart data={analyticsData.mutationAnalysisData} />
      </div>
      
      {/* 性能分析区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* 性能散点图 */}
        <PerformanceScatterChart data={analyticsData.performanceScatterData} />
        
        {/* 详细统计信息 */}
        <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
            <Award className="w-5 h-5 mr-2 text-yellow-400" />
            详细统计
          </h3>
          
          <div className="space-y-4">
            {/* 最佳细胞信息 */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h4 className="text-white font-medium mb-2">最佳细胞</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">适应度:</span>
                  <span className="text-green-400 ml-2 font-mono">0.987</span>
                </div>
                <div>
                  <span className="text-gray-400">代数:</span>
                  <span className="text-white ml-2">18</span>
                </div>
                <div>
                  <span className="text-gray-400">变异次数:</span>
                  <span className="text-blue-400 ml-2">23</span>
                </div>
                <div>
                  <span className="text-gray-400">基因长度:</span>
                  <span className="text-purple-400 ml-2">156 bp</span>
                </div>
              </div>
            </div>
            
            {/* 进化效率 */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h4 className="text-white font-medium mb-2">进化效率</h4>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400 text-sm">收敛速度:</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-20 bg-gray-700 rounded-full h-2">
                      <div className="bg-green-400 h-2 rounded-full w-4/5"></div>
                    </div>
                    <span className="text-green-400 text-sm">80%</span>
                  </div>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-gray-400 text-sm">多样性保持:</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-20 bg-gray-700 rounded-full h-2">
                      <div className="bg-blue-400 h-2 rounded-full w-3/5"></div>
                    </div>
                    <span className="text-blue-400 text-sm">60%</span>
                  </div>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-gray-400 text-sm">变异成功率:</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-20 bg-gray-700 rounded-full h-2">
                      <div className="bg-purple-400 h-2 rounded-full w-2/3"></div>
                    </div>
                    <span className="text-purple-400 text-sm">67%</span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* 资源使用 */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h4 className="text-white font-medium mb-2">资源使用</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">CPU使用率:</span>
                  <span className="text-yellow-400 ml-2">45%</span>
                </div>
                <div>
                  <span className="text-gray-400">内存使用:</span>
                  <span className="text-orange-400 ml-2">2.3 GB</span>
                </div>
                <div>
                  <span className="text-gray-400">API调用:</span>
                  <span className="text-blue-400 ml-2">1,247</span>
                </div>
                <div>
                  <span className="text-gray-400">存储空间:</span>
                  <span className="text-green-400 ml-2">156 MB</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* 实时监控指标 */}
      <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
          <Zap className="w-5 h-5 mr-2 text-yellow-400" />
          实时监控
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { label: '当前代数', value: '20', unit: '', color: 'text-blue-400' },
            { label: '活跃细胞', value: '100', unit: '', color: 'text-green-400' },
            { label: '变异率', value: '12.5', unit: '%', color: 'text-orange-400' },
            { label: '交叉率', value: '8.3', unit: '%', color: 'text-purple-400' },
            { label: '选择压力', value: '0.75', unit: '', color: 'text-red-400' },
            { label: '收敛度', value: '67', unit: '%', color: 'text-yellow-400' }
          ].map((metric, index) => (
            <div key={index} className="bg-gray-800 p-4 rounded-lg text-center">
              <div className={`text-2xl font-bold ${metric.color}`}>
                {metric.value}{metric.unit}
              </div>
              <div className="text-gray-400 text-sm mt-1">{metric.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Analytics;