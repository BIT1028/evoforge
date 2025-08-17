import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  BarChart3, 
  Brain, 
  Dna, 
  Settings, 
  Activity,
  Box
} from 'lucide-react';

/**
 * 导航项接口
 */
interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  description: string;
}

/**
 * 导航组件
 */
const Navigation: React.FC = () => {
  const location = useLocation();
  
  const navItems: NavItem[] = [
    {
      path: '/dashboard',
      label: '仪表板',
      icon: <Activity className="w-5 h-5" />,
      description: '实时监控进化状态'
    },
    {
      path: '/metagenome',
      label: 'MetaGenome',
      icon: <Dna className="w-5 h-5" />,
      description: '基因序列编辑器'
    },
    {
      path: '/simulation',
      label: '3D模拟',
      icon: <Box className="w-5 h-5" />,
      description: '3D可视化模拟'
    },
    {
      path: '/analytics',
      label: 'Analytics',
      icon: <BarChart3 className="w-5 h-5" />,
      description: '数据分析与统计'
    },
    {
      path: '/settings',
      label: '设置',
      icon: <Settings className="w-5 h-5" />,
      description: '系统配置'
    }
  ];
  
  const isActive = (path: string) => {
    return location.pathname === path;
  };
  
  return (
    <nav className="bg-black/20 backdrop-blur-sm border-b border-purple-500/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo和标题 */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Brain className="w-8 h-8 text-purple-400" />
              <h1 className="text-2xl font-bold text-white">喀迈拉计划</h1>
            </div>
          </div>
          
          {/* 导航链接 */}
          <div className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`group relative flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  isActive(item.path)
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
                title={item.description}
              >
                {item.icon}
                <span>{item.label}</span>
                
                {/* 悬浮提示 */}
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                  {item.description}
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                </div>
              </Link>
            ))}
          </div>
          
          {/* 移动端菜单按钮 */}
          <div className="md:hidden">
            <button className="text-gray-300 hover:text-white p-2">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
        
        {/* 移动端导航菜单 */}
        <div className="md:hidden border-t border-purple-500/20">
          <div className="py-2 space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-3 px-4 py-3 text-sm font-medium transition-colors ${
                  isActive(item.path)
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                {item.icon}
                <div>
                  <div>{item.label}</div>
                  <div className="text-xs text-gray-400">{item.description}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;