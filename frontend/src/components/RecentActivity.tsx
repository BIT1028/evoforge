import React from 'react';
import { Activity, Zap, Users, TrendingUp, AlertCircle } from 'lucide-react';

interface ActivityItem {
  id: string;
  type: 'generation' | 'fitness' | 'mutation' | 'error';
  message: string;
  timestamp: string;
  details?: string;
}

interface RecentActivityProps {
  activities?: ActivityItem[];
}

const RecentActivity: React.FC<RecentActivityProps> = ({ activities = [] }) => {
  // 模拟数据
  const defaultActivities: ActivityItem[] = [
    {
      id: '1',
      type: 'generation',
      message: '第15代进化完成',
      timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      details: '平均适应度: 0.756'
    },
    {
      id: '2',
      type: 'fitness',
      message: '发现新的最佳适应度',
      timestamp: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
      details: '适应度: 0.892'
    },
    {
      id: '3',
      type: 'mutation',
      message: '执行变异操作',
      timestamp: new Date(Date.now() - 18 * 60 * 1000).toISOString(),
      details: '变异率: 0.05'
    }
  ];

  const displayActivities = activities.length > 0 ? activities : defaultActivities;

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'generation':
        return Users;
      case 'fitness':
        return TrendingUp;
      case 'mutation':
        return Zap;
      case 'error':
        return AlertCircle;
      default:
        return Activity;
    }
  };

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'generation':
        return 'text-blue-400';
      case 'fitness':
        return 'text-green-400';
      case 'mutation':
        return 'text-yellow-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (minutes < 1440) return `${Math.floor(minutes / 60)}小时前`;
    return date.toLocaleDateString();
  };

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-6">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
        <Activity className="w-5 h-5 mr-2" />
        最近活动
      </h3>
      
      <div className="space-y-4">
        {displayActivities.map((activity) => {
          const Icon = getActivityIcon(activity.type);
          const colorClass = getActivityColor(activity.type);
          
          return (
            <div key={activity.id} className="flex items-start space-x-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
              <div className={`${colorClass} mt-1`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium">{activity.message}</p>
                {activity.details && (
                  <p className="text-white/60 text-xs mt-1">{activity.details}</p>
                )}
                <p className="text-white/40 text-xs mt-1">{formatTime(activity.timestamp)}</p>
              </div>
            </div>
          );
        })}
      </div>
      
      {displayActivities.length === 0 && (
        <div className="text-center py-8">
          <Activity className="w-8 h-8 text-white/20 mx-auto mb-2" />
          <p className="text-white/40 text-sm">暂无活动记录</p>
        </div>
      )}
    </div>
  );
};

export default RecentActivity;