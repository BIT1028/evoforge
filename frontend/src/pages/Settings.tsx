import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, RotateCcw, Download, Upload, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { toast } from 'sonner';

/**
 * 进化参数配置接口
 */
interface EvolutionConfig {
  populationSize: number;
  mutationRate: number;
  crossoverRate: number;
  selectionPressure: number;
  elitismRate: number;
  maxGenerations: number;
  convergenceThreshold: number;
  diversityThreshold: number;
}

/**
 * 系统配置接口
 */
interface SystemConfig {
  apiEndpoint: string;
  websocketEndpoint: string;
  maxConcurrentTasks: number;
  requestTimeout: number;
  retryAttempts: number;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  enableMetrics: boolean;
  enableAutoSave: boolean;
  autoSaveInterval: number;
}

/**
 * 渲染配置接口
 */
interface RenderConfig {
  enable3D: boolean;
  particleCount: number;
  animationSpeed: number;
  cameraDistance: number;
  lightIntensity: number;
  backgroundColor: string;
  cellColors: {
    low: string;
    medium: string;
    high: string;
    elite: string;
  };
}

/**
 * 配置节组件
 */
const ConfigSection: React.FC<{
  title: string;
  description: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}> = ({ title, description, icon, children }) => {
  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
      <div className="flex items-center mb-4">
        <div className="p-2 bg-purple-600 rounded-lg mr-3">
          {icon}
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <p className="text-gray-400 text-sm">{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
};

/**
 * 数值输入组件
 */
const NumberInput: React.FC<{
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  description?: string;
}> = ({ label, value, onChange, min, max, step = 1, unit, description }) => {
  return (
    <div className="mb-4">
      <label className="block text-white font-medium mb-2">
        {label}
        {unit && <span className="text-gray-400 ml-1">({unit})</span>}
      </label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        min={min}
        max={max}
        step={step}
        className="w-full bg-gray-800 text-white border border-gray-600 rounded-lg px-3 py-2 focus:border-purple-500 focus:outline-none"
      />
      {description && (
        <p className="text-gray-400 text-xs mt-1">{description}</p>
      )}
    </div>
  );
};

/**
 * 选择输入组件
 */
const SelectInput: React.FC<{
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  description?: string;
}> = ({ label, value, onChange, options, description }) => {
  return (
    <div className="mb-4">
      <label className="block text-white font-medium mb-2">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-gray-800 text-white border border-gray-600 rounded-lg px-3 py-2 focus:border-purple-500 focus:outline-none"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {description && (
        <p className="text-gray-400 text-xs mt-1">{description}</p>
      )}
    </div>
  );
};

/**
 * 开关输入组件
 */
const SwitchInput: React.FC<{
  label: string;
  value: boolean;
  onChange: (value: boolean) => void;
  description?: string;
}> = ({ label, value, onChange, description }) => {
  return (
    <div className="mb-4">
      <div className="flex items-center justify-between">
        <div>
          <label className="block text-white font-medium">{label}</label>
          {description && (
            <p className="text-gray-400 text-xs mt-1">{description}</p>
          )}
        </div>
        <button
          onClick={() => onChange(!value)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            value ? 'bg-purple-600' : 'bg-gray-600'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              value ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
    </div>
  );
};

/**
 * 颜色输入组件
 */
const ColorInput: React.FC<{
  label: string;
  value: string;
  onChange: (value: string) => void;
  description?: string;
}> = ({ label, value, onChange, description }) => {
  return (
    <div className="mb-4">
      <label className="block text-white font-medium mb-2">{label}</label>
      <div className="flex items-center space-x-3">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-12 h-10 rounded-lg border border-gray-600 bg-gray-800 cursor-pointer"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-gray-800 text-white border border-gray-600 rounded-lg px-3 py-2 focus:border-purple-500 focus:outline-none font-mono"
          placeholder="#000000"
        />
      </div>
      {description && (
        <p className="text-gray-400 text-xs mt-1">{description}</p>
      )}
    </div>
  );
};

/**
 * Settings主页面组件
 */
const Settings: React.FC = () => {
  // 进化参数配置
  const [evolutionConfig, setEvolutionConfig] = useState<EvolutionConfig>({
    populationSize: 100,
    mutationRate: 0.1,
    crossoverRate: 0.8,
    selectionPressure: 0.7,
    elitismRate: 0.1,
    maxGenerations: 1000,
    convergenceThreshold: 0.001,
    diversityThreshold: 0.1
  });
  
  // 系统配置
  const [systemConfig, setSystemConfig] = useState<SystemConfig>({
    apiEndpoint: 'http://localhost:8000',
    websocketEndpoint: 'ws://localhost:8000/ws',
    maxConcurrentTasks: 10,
    requestTimeout: 30000,
    retryAttempts: 3,
    logLevel: 'info',
    enableMetrics: true,
    enableAutoSave: true,
    autoSaveInterval: 300
  });
  
  // 渲染配置
  const [renderConfig, setRenderConfig] = useState<RenderConfig>({
    enable3D: true,
    particleCount: 1000,
    animationSpeed: 1.0,
    cameraDistance: 10,
    lightIntensity: 1.0,
    backgroundColor: '#1a1a2e',
    cellColors: {
      low: '#ef4444',
      medium: '#f59e0b',
      high: '#22c55e',
      elite: '#8b5cf6'
    }
  });
  
  const [selectedTab, setSelectedTab] = useState<'evolution' | 'system' | 'render'>('evolution');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  // 监听配置变化
  useEffect(() => {
    setHasUnsavedChanges(true);
  }, [evolutionConfig, systemConfig, renderConfig]);
  
  // 保存配置
  const handleSave = async () => {
    try {
      // 这里应该调用API保存配置
      console.log('[DEBUG] 保存配置', {
        evolutionConfig,
        systemConfig,
        renderConfig
      });
      
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setHasUnsavedChanges(false);
      toast.success('配置已保存');
    } catch (error) {
      console.error('[ERROR] 保存配置失败:', error);
      toast.error('保存配置失败');
    }
  };
  
  // 重置配置
  const handleReset = () => {
    if (selectedTab === 'evolution') {
      setEvolutionConfig({
        populationSize: 100,
        mutationRate: 0.1,
        crossoverRate: 0.8,
        selectionPressure: 0.7,
        elitismRate: 0.1,
        maxGenerations: 1000,
        convergenceThreshold: 0.001,
        diversityThreshold: 0.1
      });
    } else if (selectedTab === 'system') {
      setSystemConfig({
        apiEndpoint: 'http://localhost:8000',
        websocketEndpoint: 'ws://localhost:8000/ws',
        maxConcurrentTasks: 10,
        requestTimeout: 30000,
        retryAttempts: 3,
        logLevel: 'info',
        enableMetrics: true,
        enableAutoSave: true,
        autoSaveInterval: 300
      });
    } else if (selectedTab === 'render') {
      setRenderConfig({
        enable3D: true,
        particleCount: 1000,
        animationSpeed: 1.0,
        cameraDistance: 10,
        lightIntensity: 1.0,
        backgroundColor: '#1a1a2e',
        cellColors: {
          low: '#ef4444',
          medium: '#f59e0b',
          high: '#22c55e',
          elite: '#8b5cf6'
        }
      });
    }
    
    toast.success('配置已重置');
  };
  
  // 导出配置
  const handleExport = () => {
    const config = {
      evolution: evolutionConfig,
      system: systemConfig,
      render: renderConfig,
      exportedAt: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json'
    });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chimera-config-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('配置已导出');
  };
  
  // 导入配置
  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const config = JSON.parse(e.target?.result as string);
        
        if (config.evolution) setEvolutionConfig(config.evolution);
        if (config.system) setSystemConfig(config.system);
        if (config.render) setRenderConfig(config.render);
        
        toast.success('配置已导入');
      } catch (error) {
        console.error('[ERROR] 导入配置失败:', error);
        toast.error('导入配置失败：文件格式错误');
      }
    };
    reader.readAsText(file);
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center">
          <SettingsIcon className="w-8 h-8 mr-3 text-gray-400" />
          Settings - 系统设置
        </h1>
        <p className="text-gray-300">
          配置进化参数、系统设置和渲染选项
        </p>
      </div>
      
      {/* 未保存更改提示 */}
      {hasUnsavedChanges && (
        <div className="bg-yellow-600/20 border border-yellow-600/50 rounded-lg p-4 mb-6 flex items-center">
          <AlertTriangle className="w-5 h-5 text-yellow-400 mr-3" />
          <span className="text-yellow-200">
            您有未保存的更改。请记得保存配置。
          </span>
        </div>
      )}
      
      {/* 操作按钮 */}
      <div className="flex items-center space-x-4 mb-8">
        <button
          onClick={handleSave}
          className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>保存配置</span>
        </button>
        
        <button
          onClick={handleReset}
          className="flex items-center space-x-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          <span>重置当前</span>
        </button>
        
        <button
          onClick={handleExport}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          <span>导出配置</span>
        </button>
        
        <label className="flex items-center space-x-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors cursor-pointer">
          <Upload className="w-4 h-4" />
          <span>导入配置</span>
          <input
            type="file"
            accept=".json"
            onChange={handleImport}
            className="hidden"
          />
        </label>
      </div>
      
      {/* 标签页导航 */}
      <div className="flex space-x-1 mb-8">
        {[
          { id: 'evolution', label: '进化参数', icon: '🧬' },
          { id: 'system', label: '系统配置', icon: '⚙️' },
          { id: 'render', label: '渲染设置', icon: '🎨' }
        ].map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => setSelectedTab(id as any)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all ${
              selectedTab === id
                ? 'bg-purple-600 text-white shadow-lg'
                : 'text-gray-300 hover:text-white hover:bg-white/10'
            }`}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </button>
        ))}
      </div>
      
      {/* 标签页内容 */}
      <div className="space-y-8">
        {selectedTab === 'evolution' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <ConfigSection
              title="种群参数"
              description="控制进化种群的基本参数"
              icon={<Info className="w-5 h-5 text-white" />}
            >
              <NumberInput
                label="种群大小"
                value={evolutionConfig.populationSize}
                onChange={(value) => setEvolutionConfig(prev => ({ ...prev, populationSize: value }))}
                min={10}
                max={1000}
                description="每代中细胞的数量"
              />
              
              <NumberInput
                label="最大代数"
                value={evolutionConfig.maxGenerations}
                onChange={(value) => setEvolutionConfig(prev => ({ ...prev, maxGenerations: value }))}
                min={1}
                max={10000}
                description="进化过程的最大代数限制"
              />
              
              <NumberInput
                label="精英比例"
                value={evolutionConfig.elitismRate}
                onChange={(value) => setEvolutionConfig(prev => ({ ...prev, elitismRate: value }))}
                min={0}
                max={1}
                step={0.01}
                unit="%"
                description="直接保留到下一代的最优个体比例"
              />
            </ConfigSection>
            
            <ConfigSection
              title="遗传操作"
              description="控制变异和交叉操作的参数"
              icon={<CheckCircle className="w-5 h-5 text-white" />}
            >
              <NumberInput
                label="变异率"
                value={evolutionConfig.mutationRate}
                onChange={(value) => setEvolutionConfig(prev => ({ ...prev, mutationRate: value }))}
                min={0}
                max={1}
                step={0.01}
                unit="%"
                description="基因发生变异的概率"
              />
              
              <NumberInput
                label="交叉率"
                value={evolutionConfig.crossoverRate}
                onChange={(value) => setEvolutionConfig(prev => ({ ...prev, crossoverRate: value }))}
                min={0}
                max={1}
                step={0.01}
                unit="%"
                description="个体间发生基因交叉的概率"
              />
              
              <NumberInput
                label="选择压力"
                value={evolutionConfig.selectionPressure}
                onChange={(value) => setEvolutionConfig(prev => ({ ...prev, selectionPressure: value }))}
                min={0}
                max={1}
                step={0.01}
                description="适应度高的个体被选中的倾向性"
              />
            </ConfigSection>
            
            <ConfigSection
              title="收敛控制"
              description="控制进化过程收敛的条件"
              icon={<AlertTriangle className="w-5 h-5 text-white" />}
            >
              <NumberInput
                label="收敛阈值"
                value={evolutionConfig.convergenceThreshold}
                onChange={(value) => setEvolutionConfig(prev => ({ ...prev, convergenceThreshold: value }))}
                min={0.0001}
                max={0.1}
                step={0.0001}
                description="适应度改进小于此值时认为收敛"
              />
              
              <NumberInput
                label="多样性阈值"
                value={evolutionConfig.diversityThreshold}
                onChange={(value) => setEvolutionConfig(prev => ({ ...prev, diversityThreshold: value }))}
                min={0.01}
                max={1}
                step={0.01}
                description="种群多样性低于此值时触发多样性保护"
              />
            </ConfigSection>
          </div>
        )}
        
        {selectedTab === 'system' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <ConfigSection
              title="API配置"
              description="后端API和WebSocket连接设置"
              icon={<Info className="w-5 h-5 text-white" />}
            >
              <div className="mb-4">
                <label className="block text-white font-medium mb-2">API端点</label>
                <input
                  type="text"
                  value={systemConfig.apiEndpoint}
                  onChange={(e) => setSystemConfig(prev => ({ ...prev, apiEndpoint: e.target.value }))}
                  className="w-full bg-gray-800 text-white border border-gray-600 rounded-lg px-3 py-2 focus:border-purple-500 focus:outline-none"
                  placeholder="http://localhost:8000"
                />
              </div>
              
              <div className="mb-4">
                <label className="block text-white font-medium mb-2">WebSocket端点</label>
                <input
                  type="text"
                  value={systemConfig.websocketEndpoint}
                  onChange={(e) => setSystemConfig(prev => ({ ...prev, websocketEndpoint: e.target.value }))}
                  className="w-full bg-gray-800 text-white border border-gray-600 rounded-lg px-3 py-2 focus:border-purple-500 focus:outline-none"
                  placeholder="ws://localhost:8000/ws"
                />
              </div>
              
              <NumberInput
                label="请求超时"
                value={systemConfig.requestTimeout}
                onChange={(value) => setSystemConfig(prev => ({ ...prev, requestTimeout: value }))}
                min={1000}
                max={300000}
                step={1000}
                unit="ms"
                description="API请求的超时时间"
              />
            </ConfigSection>
            
            <ConfigSection
              title="性能设置"
              description="系统性能和并发控制"
              icon={<CheckCircle className="w-5 h-5 text-white" />}
            >
              <NumberInput
                label="最大并发任务"
                value={systemConfig.maxConcurrentTasks}
                onChange={(value) => setSystemConfig(prev => ({ ...prev, maxConcurrentTasks: value }))}
                min={1}
                max={100}
                description="同时执行的最大任务数"
              />
              
              <NumberInput
                label="重试次数"
                value={systemConfig.retryAttempts}
                onChange={(value) => setSystemConfig(prev => ({ ...prev, retryAttempts: value }))}
                min={0}
                max={10}
                description="请求失败时的重试次数"
              />
              
              <SelectInput
                label="日志级别"
                value={systemConfig.logLevel}
                onChange={(value) => setSystemConfig(prev => ({ ...prev, logLevel: value as any }))}
                options={[
                  { value: 'debug', label: 'Debug' },
                  { value: 'info', label: 'Info' },
                  { value: 'warn', label: 'Warning' },
                  { value: 'error', label: 'Error' }
                ]}
                description="系统日志的详细程度"
              />
            </ConfigSection>
            
            <ConfigSection
              title="功能开关"
              description="启用或禁用特定功能"
              icon={<AlertTriangle className="w-5 h-5 text-white" />}
            >
              <SwitchInput
                label="启用性能监控"
                value={systemConfig.enableMetrics}
                onChange={(value) => setSystemConfig(prev => ({ ...prev, enableMetrics: value }))}
                description="收集和显示系统性能指标"
              />
              
              <SwitchInput
                label="启用自动保存"
                value={systemConfig.enableAutoSave}
                onChange={(value) => setSystemConfig(prev => ({ ...prev, enableAutoSave: value }))}
                description="定期自动保存进化状态"
              />
              
              {systemConfig.enableAutoSave && (
                <NumberInput
                  label="自动保存间隔"
                  value={systemConfig.autoSaveInterval}
                  onChange={(value) => setSystemConfig(prev => ({ ...prev, autoSaveInterval: value }))}
                  min={60}
                  max={3600}
                  step={60}
                  unit="秒"
                  description="自动保存的时间间隔"
                />
              )}
            </ConfigSection>
          </div>
        )}
        
        {selectedTab === 'render' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <ConfigSection
              title="3D渲染"
              description="3D可视化的基本设置"
              icon={<Info className="w-5 h-5 text-white" />}
            >
              <SwitchInput
                label="启用3D渲染"
                value={renderConfig.enable3D}
                onChange={(value) => setRenderConfig(prev => ({ ...prev, enable3D: value }))}
                description="启用或禁用3D可视化效果"
              />
              
              {renderConfig.enable3D && (
                <>
                  <NumberInput
                    label="粒子数量"
                    value={renderConfig.particleCount}
                    onChange={(value) => setRenderConfig(prev => ({ ...prev, particleCount: value }))}
                    min={100}
                    max={10000}
                    step={100}
                    description="3D场景中的粒子数量"
                  />
                  
                  <NumberInput
                    label="动画速度"
                    value={renderConfig.animationSpeed}
                    onChange={(value) => setRenderConfig(prev => ({ ...prev, animationSpeed: value }))}
                    min={0.1}
                    max={5}
                    step={0.1}
                    description="动画播放的速度倍数"
                  />
                  
                  <NumberInput
                    label="相机距离"
                    value={renderConfig.cameraDistance}
                    onChange={(value) => setRenderConfig(prev => ({ ...prev, cameraDistance: value }))}
                    min={1}
                    max={50}
                    description="相机到场景中心的距离"
                  />
                </>
              )}
            </ConfigSection>
            
            <ConfigSection
              title="视觉效果"
              description="光照和颜色设置"
              icon={<CheckCircle className="w-5 h-5 text-white" />}
            >
              {renderConfig.enable3D && (
                <NumberInput
                  label="光照强度"
                  value={renderConfig.lightIntensity}
                  onChange={(value) => setRenderConfig(prev => ({ ...prev, lightIntensity: value }))}
                  min={0.1}
                  max={3}
                  step={0.1}
                  description="场景光照的强度"
                />
              )}
              
              <ColorInput
                label="背景颜色"
                value={renderConfig.backgroundColor}
                onChange={(value) => setRenderConfig(prev => ({ ...prev, backgroundColor: value }))}
                description="3D场景的背景颜色"
              />
            </ConfigSection>
            
            <ConfigSection
              title="细胞颜色"
              description="不同适应度细胞的颜色配置"
              icon={<AlertTriangle className="w-5 h-5 text-white" />}
            >
              <ColorInput
                label="低适应度细胞"
                value={renderConfig.cellColors.low}
                onChange={(value) => setRenderConfig(prev => ({
                  ...prev,
                  cellColors: { ...prev.cellColors, low: value }
                }))}
                description="适应度较低的细胞颜色"
              />
              
              <ColorInput
                label="中等适应度细胞"
                value={renderConfig.cellColors.medium}
                onChange={(value) => setRenderConfig(prev => ({
                  ...prev,
                  cellColors: { ...prev.cellColors, medium: value }
                }))}
                description="适应度中等的细胞颜色"
              />
              
              <ColorInput
                label="高适应度细胞"
                value={renderConfig.cellColors.high}
                onChange={(value) => setRenderConfig(prev => ({
                  ...prev,
                  cellColors: { ...prev.cellColors, high: value }
                }))}
                description="适应度较高的细胞颜色"
              />
              
              <ColorInput
                label="精英细胞"
                value={renderConfig.cellColors.elite}
                onChange={(value) => setRenderConfig(prev => ({
                  ...prev,
                  cellColors: { ...prev.cellColors, elite: value }
                }))}
                description="精英细胞的特殊颜色"
              />
            </ConfigSection>
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;