-- MedIQ Database Setup Script
-- Run this in your Supabase SQL Editor to create all required tables

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create user roles enum
CREATE TYPE user_role AS ENUM ('patient', 'doctor');

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role user_role NOT NULL DEFAULT 'patient',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Patient profiles table
CREATE TABLE IF NOT EXISTS patient_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date_of_birth DATE,
    gender VARCHAR(20),
    medical_history TEXT,
    allergies TEXT,
    current_medications TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(user_id)
);

-- Doctor profiles table
CREATE TABLE IF NOT EXISTS doctor_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    specialization VARCHAR(100),
    license_number VARCHAR(50),
    experience_years INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(user_id)
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    text TEXT,
    medical_data JSONB,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255),
    document_id UUID REFERENCES documents(id),
    last_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    ended_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Medical analyses table
CREATE TABLE IF NOT EXISTS medical_analyses (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    document_id UUID REFERENCES documents(id),
    symptoms JSONB,
    analysis TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Medical summaries table
CREATE TABLE IF NOT EXISTS medical_summaries (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    summary TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create Row Level Security (RLS) policies
-- These policies ensure users can only access their own data

-- Users table policy
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_select_policy ON users 
    FOR SELECT USING (auth.uid()::uuid = id);
    
CREATE POLICY users_update_policy ON users 
    FOR UPDATE USING (auth.uid()::uuid = id);

-- Patient profiles policy
ALTER TABLE patient_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY patient_profiles_select_policy ON patient_profiles 
    FOR SELECT USING (auth.uid()::uuid = user_id);
    
CREATE POLICY patient_profiles_insert_policy ON patient_profiles 
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);
    
CREATE POLICY patient_profiles_update_policy ON patient_profiles 
    FOR UPDATE USING (auth.uid()::uuid = user_id);

-- Doctor profiles policy
ALTER TABLE doctor_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY doctor_profiles_select_policy ON doctor_profiles 
    FOR SELECT USING (auth.uid()::uuid = user_id);
    
CREATE POLICY doctor_profiles_insert_policy ON doctor_profiles 
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);
    
CREATE POLICY doctor_profiles_update_policy ON doctor_profiles 
    FOR UPDATE USING (auth.uid()::uuid = user_id);

-- Documents policy
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_select_policy ON documents 
    FOR SELECT USING (auth.uid()::uuid = user_id);
    
CREATE POLICY documents_insert_policy ON documents 
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

-- Chat sessions policy
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY chat_sessions_select_policy ON chat_sessions 
    FOR SELECT USING (auth.uid()::uuid = user_id);
    
CREATE POLICY chat_sessions_insert_policy ON chat_sessions 
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

-- Chat messages policy
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY chat_messages_select_policy ON chat_messages 
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM chat_sessions 
            WHERE chat_sessions.id = chat_messages.session_id 
            AND chat_sessions.user_id = auth.uid()::uuid
        )
    );

CREATE POLICY chat_messages_insert_policy ON chat_messages 
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM chat_sessions 
            WHERE chat_sessions.id = chat_messages.session_id 
            AND chat_sessions.user_id = auth.uid()::uuid
        )
    );

-- Medical analyses policy
ALTER TABLE medical_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY medical_analyses_select_policy ON medical_analyses 
    FOR SELECT USING (auth.uid()::uuid = user_id);
    
CREATE POLICY medical_analyses_insert_policy ON medical_analyses 
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

-- Medical summaries policy
ALTER TABLE medical_summaries ENABLE ROW LEVEL SECURITY;

CREATE POLICY medical_summaries_select_policy ON medical_summaries 
    FOR SELECT USING (auth.uid()::uuid = user_id);
    
CREATE POLICY medical_summaries_insert_policy ON medical_summaries 
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

-- Create indexes for performance optimization
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_medical_analyses_user_id ON medical_analyses(user_id);
CREATE INDEX idx_medical_summaries_user_id ON medical_summaries(user_id);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = now(); 
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_timestamp
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER update_patient_profiles_timestamp
BEFORE UPDATE ON patient_profiles
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER update_doctor_profiles_timestamp
BEFORE UPDATE ON doctor_profiles
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER update_chat_sessions_timestamp
BEFORE UPDATE ON chat_sessions
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

-- Sample data for testing (optional - comment out if not needed)
-- INSERT INTO users (username, email, password, first_name, last_name, role)
-- VALUES 
--   ('testdoctor', 'doctor@example.com', '$2b$12$GqF3L4GXf55vwGctgHlTTurJu0YFHgXkEGzesRwmD2sZ/b5qMVMnC', 'John', 'Doe', 'doctor'),
--   ('testpatient', 'patient@example.com', '$2b$12$GqF3L4GXf55vwGctgHlTTurJu0YFHgXkEGzesRwmD2sZ/b5qMVMnC', 'Jane', 'Smith', 'patient');
-- 
-- -- Note: The password hash above corresponds to 'password123' for testing purposes
