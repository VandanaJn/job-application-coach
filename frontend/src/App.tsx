import { Routes, Route, Navigate } from 'react-router-dom';
import Home from './pages/Home';
import ResumeUpload from './pages/ResumeUpload';
import JobList from './pages/JobList';
import AddJob from './pages/AddJob';
import JobDetail from './pages/JobDetail';
import SessionDetail from './pages/SessionDetail';
import AnswerCoach from './pages/AnswerCoach';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/resume" element={<ResumeUpload />} />
      <Route path="/jobs" element={<JobList />} />
      <Route path="/jobs/new" element={<AddJob />} />
      <Route path="/jobs/:jobId" element={<JobDetail />} />
      <Route path="/sessions/:sessionId" element={<SessionDetail />} />
      <Route path="/sessions/:sessionId/coach" element={<AnswerCoach />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
