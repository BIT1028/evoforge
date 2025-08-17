import React, { useState } from 'react';
import { Brain, Eye, Lightbulb, AlertTriangle, MessageCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { ConsciousnessState } from '../types/evolution';

interface ConsciousnessPanelProps {
  consciousness: ConsciousnessState | null;
  className?: string;
}

const ConsciousnessPanel: React.FC<ConsciousnessPanelProps> = ({ 
  consciousness, 
  className = '' 
}) => {
  const [expandedSections, setExpandedSections] = useState<{
    insights: boolean;
    concerns: boolean;
    suggestions: boolean;
  }>({
    insights: true,
    concerns: true,
    suggestions: true
  });

  // 切换展开状态
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // 获取情绪状态颜色和图标
  const getEmotionalStateInfo = (state: string) => {
    switch (state) {
      case 'curious':
        return {
          color: 'text-blue-600 bg-blue-50 border-blue-200',
          icon: Eye,
          label: '好奇'
        };
      case 'focused':
        return {
          color: 'text-green-600 bg-green-50 border-green-200',
          icon: Brain,
          label: '专注'
        };
      case 'concerned':
        return {
          color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
          icon: AlertTriangle,
          label: '担忧'
        };
      case 'excited':
        return {
          color: 'text-purple-600 bg-purple-50 border-purple-200',
          icon: Lightbulb,
          label: '兴奋'
        };
      case 'contemplative':
        return {
          color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
          icon: MessageCircle,
          label: '沉思'
        };
      default:
        return {
          color: 'text-gray-600 bg-gray-50 border-gray-200',
          icon: Brain,
          label: '未知'
        };
    }
  };

  // 获取意识水平描述
  const getAwarenessLevelDescription = (level: number) => {
    if (level >= 0.8) return '高度清醒';
    if (level >= 0.6) return '清醒';
    if (level >= 0.4) return '一般';
    if (level >= 0.2) return '模糊';
    return '沉睡';
  };

  // 获取反思深度描述
  const getReflectionDepthDescription = (depth: number) => {
    if (depth >= 0.8) return '深度反思';
    if (depth >= 0.6) return '中度反思';
    if (depth >= 0.4) return '浅度反思';
    if (depth >= 0.2) return '表面思考';
    return '无反思';
  };

  if (!consciousness) {
    return (
      <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
        <div className="flex items-center justify-center h-32">
          <div className="text-center">
            <Brain className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p className="text-gray-500">意识系统未激活</p>
          </div>
        </div>
      </div>
    );
  }

  const emotionalInfo = getEmotionalStateInfo(consciousness.emotional_state);
  const EmotionalIcon = emotionalInfo.icon;

  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      {/* 标题和状态 */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-800 flex items-center">
          <Brain className="w-6 h-6 mr-2" />
          意识状态
        </h2>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${
            consciousness.is_active ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
          }`}></div>
          <span className={`text-sm font-medium ${
            consciousness.is_active ? 'text-green-600' : 'text-gray-600'
          }`}>
            {consciousness.is_active ? '活跃' : '休眠'}
          </span>
        </div>
      </div>

      {/* 情绪状态 */}
      <div className={`mb-6 p-4 rounded-lg border ${emotionalInfo.color}`}>
        <div className="flex items-center space-x-3">
          <EmotionalIcon className="w-6 h-6" />
          <div>
            <h3 className="font-medium">情绪状态</h3>
            <p className="text-sm opacity-80">{emotionalInfo.label}</p>
          </div>
        </div>
      </div>

      {/* 意识指标 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* 意识水平 */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <h4 className="font-medium text-gray-800 mb-2">意识水平</h4>
          <div className="flex items-center space-x-3">
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${consciousness.awareness_level * 100}%` }}
              ></div>
            </div>
            <span className="text-sm font-medium text-gray-600">
              {(consciousness.awareness_level * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {getAwarenessLevelDescription(consciousness.awareness_level)}
          </p>
        </div>

        {/* 反思深度 */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <h4 className="font-medium text-gray-800 mb-2">反思深度</h4>
          <div className="flex items-center space-x-3">
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div 
                className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${consciousness.reflection_depth * 100}%` }}
              ></div>
            </div>
            <span className="text-sm font-medium text-gray-600">
              {(consciousness.reflection_depth * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {getReflectionDepthDescription(consciousness.reflection_depth)}
          </p>
        </div>
      </div>

      {/* 当前关注点 */}
      <div className="mb-6">
        <h4 className="font-medium text-gray-800 mb-2">当前关注点</h4>
        <p className="text-gray-600 bg-gray-50 p-3 rounded-lg">
          {consciousness.current_focus || '无特定关注点'}
        </p>
      </div>

      {/* 最近反思 */}
      {consciousness.last_reflection && (
        <div className="mb-6">
          <h4 className="font-medium text-gray-800 mb-2">最近反思</h4>
          <p className="text-gray-600 bg-blue-50 p-3 rounded-lg border border-blue-200">
            {consciousness.last_reflection}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            更新时间: {new Date(consciousness.updated_at).toLocaleString()}
          </p>
        </div>
      )}

      {/* 洞察 */}
      {consciousness.insights && consciousness.insights.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => toggleSection('insights')}
            className="flex items-center justify-between w-full text-left font-medium text-gray-800 mb-2 hover:text-blue-600 transition-colors"
          >
            <span className="flex items-center">
              <Lightbulb className="w-4 h-4 mr-2" />
              洞察 ({consciousness.insights.length})
            </span>
            {expandedSections.insights ? 
              <ChevronUp className="w-4 h-4" /> : 
              <ChevronDown className="w-4 h-4" />
            }
          </button>
          {expandedSections.insights && (
            <div className="space-y-2">
              {consciousness.insights.map((insight, index) => (
                <div key={index} className="bg-green-50 p-3 rounded-lg border border-green-200">
                  <p className="text-green-800 text-sm">{insight}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 担忧 */}
      {consciousness.concerns && consciousness.concerns.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => toggleSection('concerns')}
            className="flex items-center justify-between w-full text-left font-medium text-gray-800 mb-2 hover:text-yellow-600 transition-colors"
          >
            <span className="flex items-center">
              <AlertTriangle className="w-4 h-4 mr-2" />
              担忧 ({consciousness.concerns.length})
            </span>
            {expandedSections.concerns ? 
              <ChevronUp className="w-4 h-4" /> : 
              <ChevronDown className="w-4 h-4" />
            }
          </button>
          {expandedSections.concerns && (
            <div className="space-y-2">
              {consciousness.concerns.map((concern, index) => (
                <div key={index} className="bg-yellow-50 p-3 rounded-lg border border-yellow-200">
                  <p className="text-yellow-800 text-sm">{concern}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 建议 */}
      {consciousness.suggestions && consciousness.suggestions.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => toggleSection('suggestions')}
            className="flex items-center justify-between w-full text-left font-medium text-gray-800 mb-2 hover:text-purple-600 transition-colors"
          >
            <span className="flex items-center">
              <MessageCircle className="w-4 h-4 mr-2" />
              建议 ({consciousness.suggestions.length})
            </span>
            {expandedSections.suggestions ? 
              <ChevronUp className="w-4 h-4" /> : 
              <ChevronDown className="w-4 h-4" />
            }
          </button>
          {expandedSections.suggestions && (
            <div className="space-y-2">
              {consciousness.suggestions.map((suggestion, index) => (
                <div key={index} className="bg-purple-50 p-3 rounded-lg border border-purple-200">
                  <p className="text-purple-800 text-sm">{suggestion}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConsciousnessPanel;