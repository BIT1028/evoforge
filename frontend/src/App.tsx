import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import Navigation from './components/Navigation';
import Dashboard from './pages/Dashboard';
import MetaGenome from './pages/MetaGenome';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import Simulation3D from './pages/Simulation3D';
import './App.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        {/* 导航栏 */}
        <Navigation />
        
        {/* 主要内容区域 */}
        <main>
          <Routes>
            {/* 主页重定向到仪表板 */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* 仪表板页面 */}
            <Route path="/dashboard" element={<Dashboard />} />
            
            {/* MetaGenome页面 */}
            <Route path="/metagenome" element={<MetaGenome />} />
            
            {/* Analytics页面 */}
            <Route path="/analytics" element={<Analytics />} />
            
            {/* 3D模拟页面 */}
            <Route path="/simulation" element={<Simulation3D />} />
            
            {/* 设置页面 */}
            <Route path="/settings" element={<Settings />} />
            
            {/* 404页面 */}
            <Route path="*" element={
              <div className="flex items-center justify-center min-h-[60vh]">
                <div className="text-center">
                  <h1 className="text-4xl font-bold text-gray-800 mb-4">404</h1>
                  <p className="text-gray-600 mb-4">页面未找到</p>
                  <a 
                    href="/dashboard" 
                    className="text-blue-600 hover:text-blue-800 underline"
                  >
                    返回仪表板
                  </a>
                </div>
              </div>
            } />
          </Routes>
        </main>
        
        {/* Toast通知 */}
        <Toaster 
          position="top-right"
          richColors
          closeButton
          duration={4000}
        />
      </div>
    </Router>
  );
}

export default App;