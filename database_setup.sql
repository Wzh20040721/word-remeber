-- Supabase 数据库设置脚本
-- 在 Supabase 的 SQL 编辑器中运行这些命令

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建单词表
CREATE TABLE IF NOT EXISTS words (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    word TEXT NOT NULL,
    translation TEXT NOT NULL,
    type VARCHAR(20) DEFAULT 'word', -- 'word' 或 'phrase'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    review_count INTEGER DEFAULT 0,
    last_review TIMESTAMP WITH TIME ZONE,
    next_review TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, word)
);

-- 创建索引以提高查询性能
CREATE INDEX idx_words_user_id ON words(user_id);
CREATE INDEX idx_words_next_review ON words(next_review);
CREATE INDEX idx_users_username ON users(username);

-- 启用行级安全性（RLS）
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE words ENABLE ROW LEVEL SECURITY;

-- 创建策略：用户只能访问自己的数据
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can view own words" ON words
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own words" ON words
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own words" ON words
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own words" ON words
    FOR DELETE USING (auth.uid()::text = user_id::text);