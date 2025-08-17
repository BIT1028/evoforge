-- +migrate Up
-- 创建EvoForge数据库初始表结构
-- 包含实验、个体、评估和指标表

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;

-- 实验表
CREATE TABLE experiments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    total_generations INTEGER DEFAULT 0,
    total_individuals INTEGER DEFAULT 0,
    best_fitness FLOAT,
    metadata JSONB DEFAULT '{}'
);

-- 个体表
CREATE TABLE individuals (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    generation INTEGER NOT NULL,
    genome JSONB NOT NULL,
    fitness_scores JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 评估表
CREATE TABLE evaluations (
    id SERIAL PRIMARY KEY,
    individual_id INTEGER NOT NULL REFERENCES individuals(id) ON DELETE CASCADE,
    task_id VARCHAR(255) NOT NULL,
    result JSONB,
    execution_time FLOAT,
    memory_usage BIGINT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- 指标表（时间序列数据）
CREATE TABLE metrics (
    time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    metric_name VARCHAR(255) NOT NULL,
    metric_value FLOAT NOT NULL,
    tags JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

-- 将metrics表转换为TimescaleDB超表
SELECT create_hypertable('metrics', 'time', if_not_exists => TRUE);

-- 创建索引
-- 实验表索引
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_experiments_created_at ON experiments(created_at);
CREATE INDEX idx_experiments_name ON experiments(name);

-- 个体表索引
CREATE INDEX idx_individuals_experiment_id ON individuals(experiment_id);
CREATE INDEX idx_individuals_generation ON individuals(experiment_id, generation);
CREATE INDEX idx_individuals_created_at ON individuals(created_at);
CREATE INDEX idx_individuals_fitness ON individuals USING GIN (fitness_scores);

-- 评估表索引
CREATE INDEX idx_evaluations_individual_id ON evaluations(individual_id);
CREATE INDEX idx_evaluations_task_id ON evaluations(task_id);
CREATE INDEX idx_evaluations_created_at ON evaluations(created_at);
CREATE INDEX idx_evaluations_execution_time ON evaluations(execution_time);

-- 指标表索引
CREATE INDEX idx_metrics_experiment_id ON metrics(experiment_id, time DESC);
CREATE INDEX idx_metrics_name ON metrics(metric_name, time DESC);
CREATE INDEX idx_metrics_tags ON metrics USING GIN (tags);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为实验表添加更新时间触发器
CREATE TRIGGER update_experiments_updated_at 
    BEFORE UPDATE ON experiments 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 创建数据保留策略（保留30天的指标数据）
SELECT add_retention_policy('metrics', INTERVAL '30 days', if_not_exists => TRUE);

-- 创建连续聚合视图（每小时聚合）
CREATE MATERIALIZED VIEW metrics_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS bucket,
    experiment_id,
    metric_name,
    AVG(metric_value) as avg_value,
    MAX(metric_value) as max_value,
    MIN(metric_value) as min_value,
    COUNT(*) as count
FROM metrics
GROUP BY bucket, experiment_id, metric_name;

-- 为连续聚合视图添加刷新策略
SELECT add_continuous_aggregate_policy('metrics_hourly',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- 创建每日聚合视图
CREATE MATERIALIZED VIEW metrics_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS bucket,
    experiment_id,
    metric_name,
    AVG(metric_value) as avg_value,
    MAX(metric_value) as max_value,
    MIN(metric_value) as min_value,
    COUNT(*) as count
FROM metrics
GROUP BY bucket, experiment_id, metric_name;

-- 为每日聚合视图添加刷新策略
SELECT add_continuous_aggregate_policy('metrics_daily',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- 创建一些有用的视图
-- 实验统计视图
CREATE VIEW experiment_stats AS
SELECT 
    e.id,
    e.name,
    e.status,
    e.created_at,
    e.total_generations,
    e.total_individuals,
    e.best_fitness,
    COUNT(DISTINCT i.id) as actual_individuals,
    COUNT(DISTINCT ev.id) as total_evaluations,
    AVG(ev.execution_time) as avg_execution_time
FROM experiments e
LEFT JOIN individuals i ON e.id = i.experiment_id
LEFT JOIN evaluations ev ON i.id = ev.individual_id
GROUP BY e.id, e.name, e.status, e.created_at, e.total_generations, e.total_individuals, e.best_fitness;

-- 代际统计视图
CREATE VIEW generation_stats AS
SELECT 
    i.experiment_id,
    i.generation,
    COUNT(*) as individual_count,
    AVG((SELECT AVG(value::float) FROM jsonb_each_text(i.fitness_scores))) as avg_fitness,
    MAX((SELECT AVG(value::float) FROM jsonb_each_text(i.fitness_scores))) as max_fitness,
    MIN((SELECT AVG(value::float) FROM jsonb_each_text(i.fitness_scores))) as min_fitness,
    MIN(i.created_at) as generation_start,
    MAX(i.created_at) as generation_end
FROM individuals i
WHERE i.fitness_scores IS NOT NULL
GROUP BY i.experiment_id, i.generation;

-- +migrate Down
-- 删除视图
DROP VIEW IF EXISTS generation_stats;
DROP VIEW IF EXISTS experiment_stats;

-- 删除连续聚合策略
SELECT remove_continuous_aggregate_policy('metrics_daily', if_exists => TRUE);
SELECT remove_continuous_aggregate_policy('metrics_hourly', if_exists => TRUE);

-- 删除连续聚合视图
DROP MATERIALIZED VIEW IF EXISTS metrics_daily;
DROP MATERIALIZED VIEW IF EXISTS metrics_hourly;

-- 删除保留策略
SELECT remove_retention_policy('metrics', if_exists => TRUE);

-- 删除触发器
DROP TRIGGER IF EXISTS update_experiments_updated_at ON experiments;
DROP FUNCTION IF EXISTS update_updated_at_column();

-- 删除索引（表删除时会自动删除，但为了完整性列出）
DROP INDEX IF EXISTS idx_metrics_tags;
DROP INDEX IF EXISTS idx_metrics_name;
DROP INDEX IF EXISTS idx_metrics_experiment_id;
DROP INDEX IF EXISTS idx_evaluations_execution_time;
DROP INDEX IF EXISTS idx_evaluations_created_at;
DROP INDEX IF EXISTS idx_evaluations_task_id;
DROP INDEX IF EXISTS idx_evaluations_individual_id;
DROP INDEX IF EXISTS idx_individuals_fitness;
DROP INDEX IF EXISTS idx_individuals_created_at;
DROP INDEX IF EXISTS idx_individuals_generation;
DROP INDEX IF EXISTS idx_individuals_experiment_id;
DROP INDEX IF EXISTS idx_experiments_name;
DROP INDEX IF EXISTS idx_experiments_created_at;
DROP INDEX IF EXISTS idx_experiments_status;

-- 删除表
DROP TABLE IF EXISTS metrics;
DROP TABLE IF EXISTS evaluations;
DROP TABLE IF EXISTS individuals;
DROP TABLE IF EXISTS experiments;

-- 删除扩展（谨慎操作，可能影响其他应用）
-- DROP EXTENSION IF EXISTS "timescaledb";
-- DROP EXTENSION IF EXISTS "uuid-ossp";