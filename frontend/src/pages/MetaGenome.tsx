import React, { useState, useEffect } from 'react';
import { Dna, Zap, Download, Upload, Settings } from 'lucide-react';
import { useEvolutionStore } from '../stores/evolutionStore';

/**
 * 密码子到代码分子的映射接口
 */
interface CodonMapping {
  codon: string;
  aminoAcid: string;
  moleculeType: string;
  codeTemplate: string;
  bindingSite: string;
  catalyticActivity: number;
  stability: number;
}

/**
 * 密码子映射表组件
 */
const CodonMappingTable: React.FC<{
  mappings: CodonMapping[];
  onMappingChange: (codon: string, field: string, value: any) => void;
}> = ({ mappings }) => {
  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
        <Dna className="w-5 h-5 mr-2 text-purple-400" />
        密码子映射表 (64个密码子)
      </h3>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-purple-500/20">
              <th className="text-left py-2 px-3 text-purple-300">密码子</th>
              <th className="text-left py-2 px-3 text-purple-300">氨基酸</th>
              <th className="text-left py-2 px-3 text-purple-300">分子类型</th>
              <th className="text-left py-2 px-3 text-purple-300">代码模板</th>
              <th className="text-left py-2 px-3 text-purple-300">结合位点</th>
              <th className="text-left py-2 px-3 text-purple-300">催化活性</th>
              <th className="text-left py-2 px-3 text-purple-300">稳定性</th>
            </tr>
          </thead>
          <tbody>
            {mappings.slice(0, 10).map((mapping) => (
              <tr key={mapping.codon} className="border-b border-purple-500/10 hover:bg-white/5">
                <td className="py-2 px-3 text-white font-mono">{mapping.codon}</td>
                <td className="py-2 px-3 text-gray-300">{mapping.aminoAcid}</td>
                <td className="py-2 px-3 text-blue-300">{mapping.moleculeType}</td>
                <td className="py-2 px-3 text-green-300 font-mono text-xs">
                  {mapping.codeTemplate.slice(0, 20)}...
                </td>
                <td className="py-2 px-3 text-yellow-300">{mapping.bindingSite}</td>
                <td className="py-2 px-3">
                  <div className="flex items-center space-x-2">
                    <div className="w-16 bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-green-400 h-2 rounded-full transition-all"
                        style={{ width: `${mapping.catalyticActivity * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-xs text-gray-300">
                      {(mapping.catalyticActivity * 100).toFixed(0)}%
                    </span>
                  </div>
                </td>
                <td className="py-2 px-3">
                  <div className="flex items-center space-x-2">
                    <div className="w-16 bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-blue-400 h-2 rounded-full transition-all"
                        style={{ width: `${mapping.stability * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-xs text-gray-300">
                      {(mapping.stability * 100).toFixed(0)}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {mappings.length > 10 && (
          <div className="mt-4 text-center">
            <span className="text-gray-400 text-sm">
              显示前10个密码子，共{mappings.length}个
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * 基因序列编辑器组件
 */
const GeneSequenceEditor: React.FC<{
  sequence: string;
  onSequenceChange: (sequence: string) => void;
  onMutate: () => void;
  onCrossover: () => void;
}> = ({ sequence, onSequenceChange, onMutate, onCrossover }) => {
  const [editMode, setEditMode] = useState(false);
  
  const formatSequence = (seq: string) => {
    // 每3个字符（密码子）分组显示
    return seq.match(/.{1,3}/g)?.join(' ') || seq;
  };
  
  const generateRandomSequence = (length: number = 60) => {
    const bases = ['A', 'T', 'G', 'C'];
    let newSequence = '';
    for (let i = 0; i < length; i++) {
      newSequence += bases[Math.floor(Math.random() * bases.length)];
    }
    return newSequence;
  };
  
  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center">
          <Zap className="w-5 h-5 mr-2 text-yellow-400" />
          基因序列编辑器
        </h3>
        
        <div className="flex space-x-2">
          <button
            onClick={() => setEditMode(!editMode)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              editMode
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {editMode ? '保存' : '编辑'}
          </button>
          
          <button
            onClick={() => onSequenceChange(generateRandomSequence())}
            className="px-3 py-1 rounded-md text-sm font-medium bg-purple-600 text-white hover:bg-purple-700 transition-colors"
          >
            随机生成
          </button>
        </div>
      </div>
      
      {/* 序列显示/编辑区域 */}
      <div className="mb-4">
        {editMode ? (
          <textarea
            value={sequence}
            onChange={(e) => onSequenceChange(e.target.value.toUpperCase())}
            className="w-full h-32 bg-gray-800 text-white font-mono text-sm p-3 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
            placeholder="输入DNA序列 (A, T, G, C)..."
          />
        ) : (
          <div className="bg-gray-800 p-3 rounded-lg border border-gray-600 min-h-32">
            <div className="text-white font-mono text-sm leading-relaxed">
              {formatSequence(sequence) || '暂无序列'}
            </div>
          </div>
        )}
      </div>
      
      {/* 序列信息 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-gray-800 p-3 rounded-lg">
          <div className="text-gray-400 text-xs">序列长度</div>
          <div className="text-white font-semibold">{sequence.length} bp</div>
        </div>
        <div className="bg-gray-800 p-3 rounded-lg">
          <div className="text-gray-400 text-xs">密码子数</div>
          <div className="text-white font-semibold">{Math.floor(sequence.length / 3)}</div>
        </div>
        <div className="bg-gray-800 p-3 rounded-lg">
          <div className="text-gray-400 text-xs">GC含量</div>
          <div className="text-white font-semibold">
            {sequence.length > 0 
              ? ((sequence.match(/[GC]/g)?.length || 0) / sequence.length * 100).toFixed(1)
              : 0
            }%
          </div>
        </div>
        <div className="bg-gray-800 p-3 rounded-lg">
          <div className="text-gray-400 text-xs">有效性</div>
          <div className="text-white font-semibold">
            {sequence.length % 3 === 0 ? '✓ 有效' : '✗ 无效'}
          </div>
        </div>
      </div>
      
      {/* 操作按钮 */}
      <div className="flex space-x-3">
        <button
          onClick={onMutate}
          className="flex items-center space-x-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors"
        >
          <Zap className="w-4 h-4" />
          <span>变异</span>
        </button>
        
        <button
          onClick={onCrossover}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Dna className="w-4 h-4" />
          <span>交叉</span>
        </button>
        
        <button
          className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          <span>导出</span>
        </button>
        
        <button
          className="flex items-center space-x-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
        >
          <Upload className="w-4 h-4" />
          <span>导入</span>
        </button>
      </div>
    </div>
  );
};

/**
 * MetaGenome主页面组件
 */
const MetaGenome: React.FC = () => {
  const { stats, fetchStats } = useEvolutionStore();
  const [currentSequence, setCurrentSequence] = useState('');
  const [codonMappings, setCodonMappings] = useState<CodonMapping[]>([]);
  const [selectedTab, setSelectedTab] = useState<'editor' | 'mappings' | 'analysis'>('editor');
  
  // 生成完整的64个密码子映射
  const generateCodonMappings = (): CodonMapping[] => {
    const bases = ['A', 'T', 'G', 'C'];
    const mappings: CodonMapping[] = [];
    
    const moleculeTypes = [
      '函数定义分子', '变量声明分子', '循环控制分子', '条件判断分子',
      '返回语句分子', '赋值操作分子', '算术运算分子', '逻辑运算分子',
      '比较运算分子', '字符串操作分子', '数组操作分子', '对象操作分子'
    ];
    
    const aminoAcids = [
      'Ala', 'Arg', 'Asn', 'Asp', 'Cys', 'Gln', 'Glu', 'Gly',
      'His', 'Ile', 'Leu', 'Lys', 'Met', 'Phe', 'Pro', 'Ser',
      'Thr', 'Trp', 'Tyr', 'Val', 'Stop'
    ];
    
    for (let i = 0; i < bases.length; i++) {
      for (let j = 0; j < bases.length; j++) {
        for (let k = 0; k < bases.length; k++) {
          const codon = bases[i] + bases[j] + bases[k];
          const index = mappings.length;
          
          mappings.push({
            codon,
            aminoAcid: aminoAcids[index % aminoAcids.length],
            moleculeType: moleculeTypes[index % moleculeTypes.length],
            codeTemplate: `function ${codon.toLowerCase()}() { /* ${codon} 密码子生成的代码 */ }`,
            bindingSite: `binding_${codon.toLowerCase()}`,
            catalyticActivity: Math.random(),
            stability: Math.random()
          });
        }
      }
    }
    
    return mappings;
  };
  
  // 初始化数据
  useEffect(() => {
    fetchStats();
    
    // 生成初始序列
    const initialSequence = 'ATGAAATTTGGGCCCAAATAG'; // 示例序列
    setCurrentSequence(initialSequence);
    
    // 生成密码子映射
    const mappings = generateCodonMappings();
    setCodonMappings(mappings);
    
    console.log('[DEBUG] MetaGenome页面初始化', {
      sequenceLength: initialSequence.length,
      mappingCount: mappings.length,
      stats
    });
  }, [fetchStats]);
  
  const handleMutate = () => {
    if (currentSequence.length === 0) return;
    
    const mutationRate = 0.1; // 10%变异率
    const bases = ['A', 'T', 'G', 'C'];
    let mutatedSequence = '';
    
    for (let i = 0; i < currentSequence.length; i++) {
      if (Math.random() < mutationRate) {
        // 变异：随机选择新的碱基
        mutatedSequence += bases[Math.floor(Math.random() * bases.length)];
      } else {
        mutatedSequence += currentSequence[i];
      }
    }
    
    setCurrentSequence(mutatedSequence);
    console.log('[DEBUG] 序列变异完成', {
      original: currentSequence,
      mutated: mutatedSequence,
      mutationRate
    });
  };
  
  const handleCrossover = () => {
    if (currentSequence.length < 6) return;
    
    // 简单的单点交叉
    const crossoverPoint = Math.floor(currentSequence.length / 2);
    const part1 = currentSequence.slice(0, crossoverPoint);
    const part2 = currentSequence.slice(crossoverPoint);
    
    // 生成另一个随机序列进行交叉
    const bases = ['A', 'T', 'G', 'C'];
    let randomPart = '';
    for (let i = 0; i < part2.length; i++) {
      randomPart += bases[Math.floor(Math.random() * bases.length)];
    }
    
    const crossedSequence = part1 + randomPart;
    setCurrentSequence(crossedSequence);
    
    console.log('[DEBUG] 序列交叉完成', {
      original: currentSequence,
      crossed: crossedSequence,
      crossoverPoint
    });
  };
  
  const handleMappingChange = (codon: string, field: string, value: any) => {
    setCodonMappings(prev => 
      prev.map(mapping => 
        mapping.codon === codon 
          ? { ...mapping, [field]: value }
          : mapping
      )
    );
    
    console.log('[DEBUG] 密码子映射更新', { codon, field, value });
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center">
          <Dna className="w-8 h-8 mr-3 text-purple-400" />
          MetaGenome - 元基因组编辑器
        </h1>
        <p className="text-gray-300">
          编辑和分析数字细胞的基因序列，管理密码子到代码分子的映射关系
        </p>
      </div>
      
      {/* 标签页导航 */}
      <div className="flex space-x-1 mb-8">
        {[
          { id: 'editor', label: '序列编辑器', icon: Zap },
          { id: 'mappings', label: '密码子映射', icon: Dna },
          { id: 'analysis', label: '序列分析', icon: Settings }
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
      <div className="space-y-8">
        {selectedTab === 'editor' && (
          <GeneSequenceEditor
            sequence={currentSequence}
            onSequenceChange={setCurrentSequence}
            onMutate={handleMutate}
            onCrossover={handleCrossover}
          />
        )}
        
        {selectedTab === 'mappings' && (
          <CodonMappingTable
            mappings={codonMappings}
            onMappingChange={handleMappingChange}
          />
        )}
        
        {selectedTab === 'analysis' && (
          <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
              <Settings className="w-5 h-5 mr-2 text-blue-400" />
              序列分析结果
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* 碱基组成分析 */}
              <div className="bg-gray-800 p-4 rounded-lg">
                <h4 className="text-white font-medium mb-3">碱基组成</h4>
                {['A', 'T', 'G', 'C'].map(base => {
                  const count = (currentSequence.match(new RegExp(base, 'g')) || []).length;
                  const percentage = currentSequence.length > 0 ? (count / currentSequence.length * 100) : 0;
                  
                  return (
                    <div key={base} className="flex items-center justify-between mb-2">
                      <span className="text-gray-300">{base}:</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-purple-400 h-2 rounded-full transition-all"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <span className="text-white text-sm w-12">
                          {percentage.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
              
              {/* 密码子分析 */}
              <div className="bg-gray-800 p-4 rounded-lg">
                <h4 className="text-white font-medium mb-3">密码子统计</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-300">总密码子数:</span>
                    <span className="text-white">{Math.floor(currentSequence.length / 3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">起始密码子:</span>
                    <span className="text-white">
                      {currentSequence.startsWith('ATG') ? '✓ ATG' : '✗ 无'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">终止密码子:</span>
                    <span className="text-white">
                      {['TAA', 'TAG', 'TGA'].some(stop => currentSequence.endsWith(stop)) ? '✓ 存在' : '✗ 无'}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* 预测功能 */}
              <div className="bg-gray-800 p-4 rounded-lg">
                <h4 className="text-white font-medium mb-3">功能预测</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-300">编码潜力:</span>
                    <span className="text-green-400">高</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">稳定性:</span>
                    <span className="text-blue-400">中等</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">复杂度:</span>
                    <span className="text-yellow-400">中等</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MetaGenome;