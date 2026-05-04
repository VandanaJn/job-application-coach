import { Link, useNavigate } from 'react-router-dom';
import { useJobs } from '../hooks/useJobs';
import { useUser } from '../hooks/useUser';

export default function JobList() {
  const { data: jobList, isLoading } = useJobs();
  const { data: user } = useUser();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">My Jobs</h1>
            {user?.resume_text_length && (
              <p className="text-sm text-gray-400 mt-1">Resume uploaded · {user.resume_text_length.toLocaleString()} characters</p>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => navigate('/resume')}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Update resume
            </button>
            <Link
              to="/jobs/new"
              className="px-4 py-2 text-sm bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              + Add job
            </Link>
          </div>
        </div>

        {isLoading && (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {!isLoading && jobList?.jobs.length === 0 && (
          <div className="text-center py-20">
            <p className="text-gray-400 text-lg">No jobs yet.</p>
            <p className="text-gray-400 text-sm mt-1">Add a job posting to start practising.</p>
            <Link
              to="/jobs/new"
              className="mt-6 inline-block px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Add your first job
            </Link>
          </div>
        )}

        <div className="space-y-3">
          {jobList?.jobs.map((job) => (
            <Link
              key={job.job_id}
              to={`/jobs/${job.job_id}`}
              className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-indigo-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-gray-900">
                    {job.job_title || 'Untitled role'}
                  </p>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {job.company || 'Unknown company'}
                  </p>
                </div>
                <p className="text-xs text-gray-400 mt-0.5 shrink-0 ml-4">
                  {new Date(job.created_at).toLocaleDateString()}
                </p>
              </div>
              <p className="text-sm text-gray-400 mt-3 line-clamp-2">{job.job_description}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
