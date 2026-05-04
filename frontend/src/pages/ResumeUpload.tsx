import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUploadResume } from '../hooks/useUser';

export default function ResumeUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { mutate: upload, isPending, error } = useUploadResume();

  const handleFile = (f: File) => {
    if (f.type === 'application/pdf') setFile(f);
  };

  const handleSubmit = () => {
    if (!file) return;
    upload(file, { onSuccess: () => navigate('/jobs') });
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload your resume</h1>
        <p className="text-gray-500 mb-8">Upload once — use it across all your job practice sessions.</p>

        <div
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
            dragOver ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-indigo-400'
          }`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
          {file ? (
            <div>
              <p className="text-indigo-600 font-medium text-lg">{file.name}</p>
              <p className="text-gray-400 text-sm mt-1">{(file.size / 1024).toFixed(0)} KB</p>
            </div>
          ) : (
            <div>
              <p className="text-gray-500">Drag & drop your PDF here, or click to browse</p>
              <p className="text-gray-400 text-sm mt-1">PDF files only</p>
            </div>
          )}
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600">{(error as Error).message}</p>
        )}

        <button
          onClick={handleSubmit}
          disabled={!file || isPending}
          className="mt-6 w-full py-3 px-4 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isPending ? 'Uploading…' : 'Continue'}
        </button>
      </div>
    </div>
  );
}
