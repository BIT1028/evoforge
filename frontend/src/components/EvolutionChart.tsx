import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar
} from 'recharts';
import { EvolutionStats } from '../types/evolution';

interface EvolutionChartProps {
  stats: EvolutionStats;
  type: 'fitness' | 'diversity' | 'performance' | 'distribution';
  className?: string;
}

const EvolutionChart: React.FC<EvolutionChartProps> = ({ stats, type, className = '' }) => {
  // 准备图表数据
  const chartData = useMemo(() => {
    const maxLength = Math.max(
      stats.average_fitness_trend.length,
      stats.best_fitness_trend.length,
      stats.diversity_trend.length
    );

    return Array.from({ length: maxLength }, (_, index) => ({
      generation: index + 1,
      averageFitness: stats.average_fitness_trend[index] || 0,
      bestFitness: stats.best_fitness_trend[index] || 0,
      diversity: stats.diversity_trend[index] || 0,
      improvement: index > 0 ? 
        (stats.best_fitness_trend[index] || 0) - (stats.best_fitness_trend[index - 1] || 0) : 0
    }));
  }, [stats]);

  // 性能数据
  const performanceData = useMemo(() => [
    {
      metric: 'API调用',
      value: stats.api_calls_total,
      unit: '次'
    },
    {
      metric: 'API成本',
      value: stats.api_cost_total,
      unit: '$'
    },
    {
      metric: '细胞/秒',
      value: stats.cells_per_second,
      unit: 'cells/s'
    },
    {
      metric: '运行时间',
      value: stats.runtime_seconds,
      unit: '秒'
    }
  ], [stats]);

  // 适应度分布数据（模拟）
  const distributionData = useMemo(() => {
    const bins = 10;
    const minFitness = 0;
    const maxFitness = stats.best_fitness_ever || 100;
    const binSize = (maxFitness - minFitness) / bins;
    
    return Array.from({ length: bins }, (_, index) => {
      const binStart = minFitness + index * binSize;
      const binEnd = binStart + binSize;
      const binCenter = (binStart + binEnd) / 2;
      
      // 模拟正态分布
      const count = Math.max(0, Math.round(
        stats.total_cells * 0.1 * Math.exp(-Math.pow((binCenter - stats.best_fitness_ever * 0.7) / (stats.best_fitness_ever * 0.2), 2))
      ));
      
      return {
        fitness: binCenter.toFixed(1),
        count,
        range: `${binStart.toFixed(1)}-${binEnd.toFixed(1)}`
      };
    });
  }, [stats]);

  // 自定义Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-300 rounded-lg shadow-lg">
          <p className="font-medium text-gray-800">{`代数: ${label}`}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
              {`${entry.name}: ${entry.value.toFixed(3)}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // 渲染适应度趋势图
  const renderFitnessChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis 
          dataKey="generation" 
          stroke="#666"
          fontSize={12}
        />
        <YAxis 
          stroke="#666"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Line
          type="monotone"
          dataKey="bestFitness"
          stroke="#10b981"
          strokeWidth={2}
          name="最佳适应度"
          dot={{ fill: '#10b981', strokeWidth: 2, r: 3 }}
        />
        <Line
          type="monotone"
          dataKey="averageFitness"
          stroke="#3b82f6"
          strokeWidth={2}
          name="平均适应度"
          dot={{ fill: '#3b82f6', strokeWidth: 2, r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );

  // 渲染多样性图
  const renderDiversityChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis 
          dataKey="generation" 
          stroke="#666"
          fontSize={12}
        />
        <YAxis 
          stroke="#666"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Area
          type="monotone"
          dataKey="diversity"
          stroke="#8b5cf6"
          fill="#8b5cf6"
          fillOpacity={0.3}
          name="种群多样性"
        />
      </AreaChart>
    </ResponsiveContainer>
  );

  // 渲染性能图
  const renderPerformanceChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={performanceData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis 
          dataKey="metric" 
          stroke="#666"
          fontSize={12}
        />
        <YAxis 
          stroke="#666"
          fontSize={12}
        />
        <Tooltip 
          formatter={(value: any, _name: any, props: any) => [
             `${value} ${props.payload.unit}`,
             _name
          ]}
        />
        <Bar 
          dataKey="value" 
          fill="#f59e0b"
          name="性能指标"
        />
      </BarChart>
    </ResponsiveContainer>
  );

  // 渲染适应度分布图
  const renderDistributionChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={distributionData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis 
          dataKey="fitness" 
          stroke="#666"
          fontSize={12}
        />
        <YAxis 
          stroke="#666"
          fontSize={12}
        />
        <Tooltip 
          formatter={(value: any, _name: any, props: any) => [
            `${value} 个细胞`,
            `适应度范围: ${props.payload.range}`
          ]}
        />
        <Bar 
          dataKey="count" 
          fill="#ef4444"
          name="细胞数量"
        />
      </BarChart>
    </ResponsiveContainer>
  );

  // 获取图表标题
  const getChartTitle = () => {
    switch (type) {
      case 'fitness':
        return '适应度趋势';
      case 'diversity':
        return '种群多样性';
      case 'performance':
        return '性能指标';
      case 'distribution':
        return '适应度分布';
      default:
        return '进化图表';
    }
  };

  // 渲染对应的图表
  const renderChart = () => {
    switch (type) {
      case 'fitness':
        return renderFitnessChart();
      case 'diversity':
        return renderDiversityChart();
      case 'performance':
        return renderPerformanceChart();
      case 'distribution':
        return renderDistributionChart();
      default:
        return renderFitnessChart();
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        {getChartTitle()}
      </h3>
      
      {/* 图表容器 */}
      <div className="w-full">
        {renderChart()}
      </div>
      
      {/* 图表说明 */}
      <div className="mt-4 text-sm text-gray-600">
        {type === 'fitness' && (
          <p>显示每代的最佳和平均适应度变化趋势</p>
        )}
        {type === 'diversity' && (
          <p>显示种群多样性随代数的变化，高多样性有助于避免早熟收敛</p>
        )}
        {type === 'performance' && (
          <p>显示系统性能指标，包括API调用次数、成本和处理速度</p>
        )}
        {type === 'distribution' && (
          <p>显示当前种群中细胞适应度的分布情况</p>
        )}
      </div>
    </div>
  );
};

export default EvolutionChart;