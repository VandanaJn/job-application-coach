import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateJob } from '../hooks/useJobs';

type Mode = 'url' | 'text';

export default function AddJob() {
  const [mode, setMode] = useState<Mode>('text');
  const [url, setUrl] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [description, setDescription] = useState('');
  const navigate = useNavigate();
  const { mutate: createJob, isPending, error } = useCreateJob();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const body = mode === 'url'
      ? { url }
      : { job_title: jobTitle, company, job_description: description };
    createJob(body, { onSuccess: (job) => navigate(`/jobs/${job.job_id}`) });
  };

  const canSubmit = mode === 'url' ? url.trim().length > 0 : description.trim().length > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <button onClick={() => navigate('/jobs')} className="text-sm text-gray-400 hover:text-gray-600 mb-6 flex items-center gap-1">
          ← Back
        </button>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">Add a job</h1>
        <p className="text-gray-500 mb-8">Paste the job description or provide a URL to scrape it.</p>

        <div className="flex gap-2 mb-6">
          {(['text', 'url'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                mode === m
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {m === 'text' ? 'Paste text' : 'From URL'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'url' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Job posting URL</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/jobs/senior-engineer"
                className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-xs text-gray-400 mt-1">Note: LinkedIn, Indeed, and Glassdoor block scraping — paste text instead for those.</p>
            </div>
          ) : (
            <>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Job title</label>
                  <input
                    type="text"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    placeholder="Senior Engineer"
                    className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                  <input
                    type="text"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    placeholder="Acme Corp"
                    className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Job description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={10}
                  placeholder="Paste the full job description here…"
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
                />
              </div>
            </>
          )}

          {error && (
            <p className="text-sm text-red-600">{(error as Error).message}</p>
          )}

          <button
            type="submit"
            disabled={!canSubmit || isPending}
            className="w-full py-3 px-4 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isPending ? 'Saving…' : 'Save job'}
          </button>
        </form>
      </div>
    </div>
  );
}
