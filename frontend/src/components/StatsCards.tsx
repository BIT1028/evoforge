import React from 'react';
import { TrendingUp, Users, Zap, Clock } from 'lucide-react';
import { EvolutionStats } from '../types/evolution';

interface StatsCardsProps {
  stats: EvolutionStats | null;
}

const StatsCards: React.FC<StatsCardsProps> = ({ stats }) => {
  const cards = [
    {
      title: '当前代数',
      value: stats?.current_generation || 0,
      icon: TrendingUp,
      color: 'bg-blue-500',
      change: '+1'
    },
    {
      title: '细胞总数',
      value: stats?.total_cells || 0,
      icon: Users,
      color: 'bg-green-500',
      change: `+${stats?.total_cells || 0}`
    },
    {
      title: '最佳适应度',
      value: stats?.best_fitness_ever?.toFixed(3) || '0.000',
      icon: Zap,
      color: 'bg-yellow-500',
      change: '+0.001'
    },
    {
      title: '运行时间',
      value: `${Math.floor((stats?.runtime_seconds || 0) / 60)}m`,
      icon: Clock,
      color: 'bg-purple-500',
      change: '+1m'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {cards.map((card, index) => {
        const Icon = card.icon;
        return (
          <div key={index} className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/60 text-sm font-medium">{card.title}</p>
                <p className="text-2xl font-bold text-white mt-1">{card.value}</p>
              </div>
              <div className={`${card.color} p-3 rounded-lg`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="mt-4 flex items-center">
              <span className="text-green-400 text-sm font-medium">{card.change}</span>
              <span className="text-white/60 text-sm ml-2">较上次</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default StatsCards;