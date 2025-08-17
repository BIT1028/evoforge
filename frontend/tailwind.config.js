/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // 自定义颜色
      colors: {
        // 主品牌色
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // 次要色
        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        // 成功色
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16',
        },
        // 警告色
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
          950: '#451a03',
        },
        // 错误色
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
          950: '#450a0a',
        },
        // 进化主题色
        evolution: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
          700: '#7c3aed',
          800: '#6b21a8',
          900: '#581c87',
          950: '#3b0764',
        },
        // 意识主题色
        consciousness: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
          950: '#082f49',
        },
      },
      
      // 自定义字体
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        display: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      
      // 自定义字体大小
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.75rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1' }],
        '6xl': ['3.75rem', { lineHeight: '1' }],
        '7xl': ['4.5rem', { lineHeight: '1' }],
        '8xl': ['6rem', { lineHeight: '1' }],
        '9xl': ['8rem', { lineHeight: '1' }],
      },
      
      // 自定义间距
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
        '144': '36rem',
      },
      
      // 自定义圆角
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },
      
      // 自定义阴影
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'medium': '0 4px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        'strong': '0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'glow': '0 0 20px rgba(59, 130, 246, 0.3)',
        'glow-green': '0 0 20px rgba(34, 197, 94, 0.3)',
        'glow-red': '0 0 20px rgba(239, 68, 68, 0.3)',
        'glow-purple': '0 0 20px rgba(168, 85, 247, 0.3)',
      },
      
      // 自定义动画
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'fade-out': 'fadeOut 0.5s ease-in-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'slide-in-left': 'slideInLeft 0.3s ease-out',
        'slide-in-up': 'slideInUp 0.3s ease-out',
        'slide-in-down': 'slideInDown 0.3s ease-out',
        'bounce-soft': 'bounceSoft 1s infinite',
        'pulse-soft': 'pulseSoft 2s infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 3s ease-in-out infinite',
        'wiggle': 'wiggle 1s ease-in-out infinite',
      },
      
      // 自定义关键帧
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInLeft: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInUp: {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideInDown: {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        bounceSoft: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(59, 130, 246, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(59, 130, 246, 0.8)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(-3deg)' },
          '50%': { transform: 'rotate(3deg)' },
        },
      },
      
      // 自定义背景图案
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'grid-pattern': 'url("data:image/svg+xml,%3csvg width=\'40\' height=\'40\' viewBox=\'0 0 40 40\' xmlns=\'http://www.w3.org/2000/svg\'%3e%3cg fill=\'%23f3f4f6\' fill-opacity=\'0.4\' fill-rule=\'evenodd\'%3e%3cpath d=\'m0 40l40-40h-40v40zm40 0v-40h-40l40 40z\'/%3e%3c/g%3e%3c/svg%3e")',
        'dot-pattern': 'url("data:image/svg+xml,%3csvg width=\'20\' height=\'20\' viewBox=\'0 0 20 20\' xmlns=\'http://www.w3.org/2000/svg\'%3e%3cg fill=\'%23f3f4f6\' fill-opacity=\'0.4\' fill-rule=\'evenodd\'%3e%3ccircle cx=\'3\' cy=\'3\' r=\'3\'/%3e%3c/g%3e%3c/svg%3e")',
      },
      
      // 自定义屏幕尺寸
      screens: {
        'xs': '475px',
        '3xl': '1600px',
      },
      
      // 自定义容器
      container: {
        center: true,
        padding: {
          DEFAULT: '1rem',
          sm: '2rem',
          lg: '4rem',
          xl: '5rem',
          '2xl': '6rem',
        },
      },
      
      // 自定义z-index
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      },
    },
  },
  plugins: [
    // 表单插件
    require('@tailwindcss/forms')({
      strategy: 'class', // 使用class策略
    }),
    
    // 排版插件
    require('@tailwindcss/typography'),
    
    // 容器查询插件
    require('@tailwindcss/container-queries'),
    
    // 自定义插件
    function({ addUtilities, addComponents, theme }) {
      // 添加自定义工具类
      addUtilities({
        '.text-shadow': {
          textShadow: '0 2px 4px rgba(0,0,0,0.10)',
        },
        '.text-shadow-md': {
          textShadow: '0 4px 8px rgba(0,0,0,0.12), 0 2px 4px rgba(0,0,0,0.08)',
        },
        '.text-shadow-lg': {
          textShadow: '0 15px 35px rgba(0,0,0,0.1), 0 5px 15px rgba(0,0,0,0.07)',
        },
        '.text-shadow-none': {
          textShadow: 'none',
        },
        '.backface-hidden': {
          backfaceVisibility: 'hidden',
        },
        '.perspective-1000': {
          perspective: '1000px',
        },
        '.transform-style-3d': {
          transformStyle: 'preserve-3d',
        },
      });
      
      // 添加自定义组件
      addComponents({
        '.btn': {
          padding: `${theme('spacing.2')} ${theme('spacing.4')}`,
          borderRadius: theme('borderRadius.md'),
          fontWeight: theme('fontWeight.medium'),
          fontSize: theme('fontSize.sm'),
          lineHeight: theme('lineHeight.5'),
          transition: 'all 0.2s ease-in-out',
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          '&:focus': {
            outline: 'none',
            boxShadow: `0 0 0 3px ${theme('colors.blue.500')}40`,
          },
          '&:disabled': {
            opacity: '0.5',
            cursor: 'not-allowed',
          },
        },
        '.card': {
          backgroundColor: theme('colors.white'),
          borderRadius: theme('borderRadius.lg'),
          boxShadow: theme('boxShadow.md'),
          border: `1px solid ${theme('colors.gray.200')}`,
          overflow: 'hidden',
        },
        '.input': {
          width: '100%',
          padding: `${theme('spacing.2')} ${theme('spacing.3')}`,
          border: `1px solid ${theme('colors.gray.300')}`,
          borderRadius: theme('borderRadius.md'),
          fontSize: theme('fontSize.sm'),
          lineHeight: theme('lineHeight.5'),
          transition: 'all 0.2s ease-in-out',
          '&:focus': {
            outline: 'none',
            borderColor: theme('colors.blue.500'),
            boxShadow: `0 0 0 3px ${theme('colors.blue.500')}20`,
          },
        },
      });
    },
  ],
  
  // 暗色模式配置
  darkMode: 'class',
  
  // 重要性前缀
  important: false,
  
  // 前缀
  prefix: '',
  
  // 分隔符
  separator: ':',
  
  // 核心插件配置
  corePlugins: {
    // 禁用某些核心插件
    // preflight: false,
  },
};