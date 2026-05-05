export interface UserProfile {
  user_id: string;
  has_resume: boolean;
  resume_text_length?: number;
}

export interface UserResumeResponse {
  user_id: string;
  resume_text_length: number;
  s3_pdf_key: string;
  uploaded_at: string;
}

export interface Job {
  job_id: string;
  job_title?: string;
  company?: string;
  job_description: string;
  created_at: string;
}

export interface JobListResponse {
  jobs: Job[];
}

export interface JobCreate {
  url?: string;
  job_title?: string;
  company?: string;
  job_description?: string;
}

export interface Session {
  session_id: string;
  job_id: string;
  status: string;
  created_at: string;
}

export interface SessionListResponse {
  sessions: Session[];
}

export interface QuestionItem {
  question: string;
  category: string;
}

export interface SessionStatus {
  session_id: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  questions?: QuestionItem[];
  error?: string;
}
