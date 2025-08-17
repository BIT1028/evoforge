import React, { Suspense, useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Sphere, Box } from '@react-three/drei';
import { Play, Pause, RotateCcw, Settings, Zap, Activity } from 'lucide-react';
import * as THREE from 'three';
import { useEvolutionStore } from '../stores/evolutionStore';

/**
 * 数字细胞3D可视化组件
 * 在3D空间中展示进化过程中的数字细胞
 */
interface DigitalCell3D {
  id: string;
  position: [number, number, number];
  fitness: number;
  generation: number;
  isActive: boolean;
  velocity: [number, number, number];
}

/**
 * 单个数字细胞的3D渲染组件
 */
const Cell3D: React.FC<{ cell: DigitalCell3D }> = ({ cell }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  
  // 根据适应度计算颜色
  const getColor = () => {
    const fitness = Math.max(0, Math.min(1, cell.fitness));
    return new THREE.Color().setHSL(fitness * 0.3, 0.8, 0.5); // 红色到绿色渐变
  };
  
  // 根据适应度计算大小
  const getSize = () => {
    return 0.1 + (cell.fitness * 0.3);
  };
  
  useFrame((_, delta) => {
    if (meshRef.current) {
      // 细胞运动模拟
      meshRef.current.position.x += cell.velocity[0] * delta;
      meshRef.current.position.y += cell.velocity[1] * delta;
      meshRef.current.position.z += cell.velocity[2] * delta;
      
      // 边界检测
      if (Math.abs(meshRef.current.position.x) > 5) {
        cell.velocity[0] *= -1;
      }
      if (Math.abs(meshRef.current.position.y) > 5) {
        cell.velocity[1] *= -1;
      }
      if (Math.abs(meshRef.current.position.z) > 5) {
        cell.velocity[2] *= -1;
      }
      
      // 悬浮动画
      if (hovered) {
        meshRef.current.rotation.x += delta * 2;
        meshRef.current.rotation.y += delta * 2;
      }
    }
  });
  
  return (
    <Sphere
      ref={meshRef}
      position={cell.position}
      args={[getSize(), 16, 16]}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    >
      <meshStandardMaterial
        color={getColor()}
        emissive={hovered ? getColor().multiplyScalar(0.3) : new THREE.Color(0, 0, 0)}
        transparent
        opacity={cell.isActive ? 1.0 : 0.6}
      />
      {hovered && (
        <Text
          position={[0, getSize() + 0.3, 0]}
          fontSize={0.1}
          color="white"
          anchorX="center"
          anchorY="middle"
        >
          {`ID: ${cell.id.slice(0, 8)}\nFitness: ${cell.fitness.toFixed(3)}\nGen: ${cell.generation}`}
        </Text>
      )}
    </Sphere>
  );
};

/**
 * 3D环境组件
 */
const Environment3D: React.FC = () => {
  return (
    <>
      {/* 环境光 */}
      <ambientLight intensity={0.4} />
      
      {/* 主光源 */}
      <directionalLight
        position={[10, 10, 5]}
        intensity={1}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      
      {/* 点光源 */}
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#ff6b6b" />
      <pointLight position={[10, -10, 10]} intensity={0.5} color="#4ecdc4" />
      
      {/* 网格地面 */}
      <gridHelper args={[20, 20, '#444444', '#222222']} position={[0, -5, 0]} />
      
      {/* 边界框 */}
      <Box position={[0, 0, 0]} args={[10, 10, 10]}>
        <meshBasicMaterial color="#333333" transparent opacity={0.1} />
      </Box>
    </>
  );
};

/**
 * 3D模拟主组件
 */
const Simulation3D: React.FC = () => {
  const { stats, status, fetchStats, fetchStatus } = useEvolutionStore();
  const [isPlaying, setIsPlaying] = useState(false);
  const [simulationSpeed, setSimulationSpeed] = useState(1);
  const [showStats, setShowStats] = useState(true);
  const [cells, setCells] = useState<DigitalCell3D[]>([]);
  
  // 生成模拟细胞数据
  const generateCells = (count: number): DigitalCell3D[] => {
    const newCells: DigitalCell3D[] = [];
    
    for (let i = 0; i < count; i++) {
      newCells.push({
        id: `cell_${i}`,
        position: [
          (Math.random() - 0.5) * 8,
          (Math.random() - 0.5) * 8,
          (Math.random() - 0.5) * 8
        ],
        fitness: Math.random(),
        generation: stats?.current_generation || 0,
        isActive: Math.random() > 0.3,
        velocity: [
          (Math.random() - 0.5) * 0.5,
          (Math.random() - 0.5) * 0.5,
          (Math.random() - 0.5) * 0.5
        ]
      });
    }
    
    return newCells;
  };
  
  // 初始化和更新数据
  useEffect(() => {
    fetchStats();
    fetchStatus();
    
    // 生成初始细胞
    const initialCells = generateCells(20);
    setCells(initialCells);
    
    console.log('[DEBUG] 3D模拟初始化完成', {
      cellCount: initialCells.length,
      stats,
      status
    });
  }, [fetchStats, fetchStatus]);
  
  // 定期更新数据
  useEffect(() => {
    if (!isPlaying) return;
    
    const interval = setInterval(() => {
      fetchStats();
      
      // 更新细胞数据
      setCells(prevCells => {
        return prevCells.map(cell => ({
          ...cell,
          fitness: Math.max(0, Math.min(1, cell.fitness + (Math.random() - 0.5) * 0.1)),
          generation: stats?.current_generation || cell.generation
        }));
      });
      
      console.log('[DEBUG] 3D模拟数据更新', {
        isPlaying,
        cellCount: cells.length,
        currentGeneration: stats?.current_generation
      });
    }, 1000 / simulationSpeed);
    
    return () => clearInterval(interval);
  }, [isPlaying, simulationSpeed, fetchStats, stats?.current_generation]);
  
  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
    console.log('[DEBUG] 3D模拟播放状态切换', { isPlaying: !isPlaying });
  };
  
  const handleReset = () => {
    setIsPlaying(false);
    const newCells = generateCells(20);
    setCells(newCells);
    console.log('[DEBUG] 3D模拟重置', { newCellCount: newCells.length });
  };
  
  const handleSpeedChange = (speed: number) => {
    setSimulationSpeed(speed);
    console.log('[DEBUG] 3D模拟速度变更', { speed });
  };
  
  return (
    <div className="h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 relative">
      {/* 控制面板 */}
      <div className="absolute top-4 left-4 z-10 bg-black/20 backdrop-blur-sm rounded-lg p-4 border border-purple-500/20">
        <div className="flex items-center space-x-4 mb-4">
          <button
            onClick={handlePlayPause}
            className={`p-2 rounded-lg transition-colors ${
              isPlaying
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          </button>
          
          <button
            onClick={handleReset}
            className="p-2 rounded-lg bg-gray-600 hover:bg-gray-700 text-white transition-colors"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => setShowStats(!showStats)}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
        
        {/* 速度控制 */}
        <div className="mb-4">
          <label className="block text-white text-sm mb-2">模拟速度</label>
          <div className="flex space-x-2">
            {[0.5, 1, 2, 4].map(speed => (
              <button
                key={speed}
                onClick={() => handleSpeedChange(speed)}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  simulationSpeed === speed
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {speed}x
              </button>
            ))}
          </div>
        </div>
        
        {/* 状态信息 */}
        {showStats && (
          <div className="text-white text-sm space-y-2">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-green-400" />
              <span>状态: {status || '未知'}</span>
            </div>
            <div className="flex items-center space-x-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              <span>细胞数: {cells.length}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-4 h-4 bg-blue-400 rounded-full"></span>
              <span>代数: {stats?.current_generation || 0}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-4 h-4 bg-green-400 rounded-full"></span>
              <span>最佳适应度: {stats?.best_fitness_ever?.toFixed(3) || '0.000'}</span>
            </div>
          </div>
        )}
      </div>
      
      {/* 3D画布 */}
      <Canvas
        camera={{ position: [10, 10, 10], fov: 60 }}
        shadows
        className="w-full h-full"
        onCreated={({ gl }) => {
          gl.setClearColor('#0a0a0a');
          console.log('[DEBUG] 3D Canvas 创建成功', {
            renderer: gl.info.render,
            memory: gl.info.memory
          });
        }}
      >
        <Suspense fallback={null}>
          <Environment3D />
          
          {/* 渲染所有细胞 */}
          {cells.map(cell => (
            <Cell3D key={cell.id} cell={cell} />
          ))}
          
          {/* 轨道控制器 */}
          <OrbitControls
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            minDistance={5}
            maxDistance={50}
          />
        </Suspense>
      </Canvas>
      
      {/* 加载提示 */}
      <div className="absolute bottom-4 right-4 text-white text-sm bg-black/20 backdrop-blur-sm rounded-lg p-2">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${
            isPlaying ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
          }`}></div>
          <span>{isPlaying ? '模拟运行中' : '模拟已暂停'}</span>
        </div>
      </div>
    </div>
  );
};

export default Simulation3D;