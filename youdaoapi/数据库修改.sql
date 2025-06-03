-- 创建作文表
CREATE TABLE IF NOT EXISTS writing(
    id UUID DEFAULT gen_random_uuid() primary key,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    rawEssay text NOT NULL,
    modelContent text,
    isNeedSynoyms boolean default false,
    correctVersion varchar(20) default 'basic',
    isNeedEssayReport boolean default false,
    sentNum integer default 0,
    essayAdvice text,
    totalScore integer default 0,
    totalEvaluation varchar(30) ,
    majaor


)
