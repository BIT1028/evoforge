import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // 路径别名
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@stores': path.resolve(__dirname, './src/stores'),
      '@services': path.resolve(__dirname, './src/services'),
      '@types': path.resolve(__dirname, './src/types'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
  
  // 开发服务器配置
  server: {
    port: 3000,
    host: true, // 允许外部访问
    open: true, // 自动打开浏览器
    cors: true, // 启用CORS
    proxy: {
      // 代理API请求到后端
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true, // 支持WebSocket
      },
      // WebSocket代理
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  
  // 构建配置
  build: {
    outDir: 'dist',
    sourcemap: true, // 生成源码映射
    minify: 'terser', // 使用terser压缩
    target: 'es2020', // 目标ES版本
    
    // 代码分割
    rollupOptions: {
      output: {
        manualChunks: {
          // 将React相关库分离到单独的chunk
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // 将图表库分离
          'chart-vendor': ['recharts'],
          // 将状态管理库分离
          'state-vendor': ['zustand'],
          // 将工具库分离
          'utils-vendor': ['axios'],
          // 将UI库分离
          'ui-vendor': ['lucide-react', 'sonner'],
        },
      },
    },
    
    // 优化配置
    terserOptions: {
      compress: {
        drop_console: true, // 生产环境移除console
        drop_debugger: true, // 移除debugger
      },
    },
    
    // 资源处理
    assetsDir: 'assets',
    assetsInlineLimit: 4096, // 小于4kb的资源内联为base64
  },
  
  // 预览服务器配置（用于预览构建结果）
  preview: {
    port: 4173,
    host: true,
    cors: true,
  },
  
  // 环境变量配置
  envPrefix: 'VITE_', // 环境变量前缀
  
  // CSS配置
  css: {
    devSourcemap: true, // 开发环境CSS源码映射
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@/styles/variables.scss";`, // 全局SCSS变量
      },
    },
  },
  
  // 依赖优化
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'zustand',
      'axios',
      'recharts',
      'lucide-react',
      'sonner',
    ],
    exclude: [
      // 排除某些依赖的预构建
    ],
  },
  
  // 定义全局常量
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  
  // 实验性功能
  experimental: {
    // 启用构建时的依赖分析
    buildAdvancedBaseOptions: {
      // 高级基础选项
    },
  },
  
  // 日志级别
  logLevel: 'info',
  
  // 清除控制台
  clearScreen: false,
});