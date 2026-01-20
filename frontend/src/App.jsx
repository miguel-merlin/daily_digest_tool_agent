import { useState } from "react";
import "./App.css";

function App() {
  const [files, setFiles] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [resultId, setResultId] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
      setResultId(null); // Reset result on new upload
    }
  };

  const handleGenerate = async () => {
    if (files.length === 0) return;

    setIsGenerating(true);
    setResultId(null);

    // Simulate API call
    try {
      // In a real app, we would use FormData to send files to the backend
      // const formData = new FormData();
      // files.forEach(file => formData.append('files', file));
      // await fetch('/api/v1/ingest/slack', { method: 'POST', body: formData });

      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Generate a fake ID like "dig_001" from the docs
      const fakeId = `dig_${Math.floor(Math.random() * 1000)
        .toString()
        .padStart(3, "0")}`;
      setResultId(fakeId);
    } catch (error) {
      console.error("Error generating digest:", error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Daily Digest Tool for Hardware Engineering Teams</h1>
      </header>

      <main>
        <div className="card upload-card">
          <h2>Upload Conversations</h2>
          <p className="instruction-text">
            Select one or more JSON files containing Slack exports.
          </p>

          <div className="file-input-wrapper">
            <input
              type="file"
              multiple
              accept=".json"
              onChange={handleFileChange}
              id="file-upload"
              className="file-input"
            />
            <label htmlFor="file-upload" className="file-label">
              {files.length > 0
                ? `${files.length} file(s) selected`
                : "Choose Files"}
            </label>
          </div>

          {files.length > 0 && (
            <ul className="file-list">
              {files.map((file, index) => (
                <li key={index} className="file-item">
                  📄 {file.name}
                </li>
              ))}
            </ul>
          )}

          <div className="actions">
            <button
              className="primary-button"
              onClick={handleGenerate}
              disabled={files.length === 0 || isGenerating}
            >
              {isGenerating ? (
                <span className="loading-state">Generating...</span>
              ) : (
                "Generate Daily Reports"
              )}
            </button>
          </div>
        </div>

        {resultId && (
          <div className="card result-card fade-in">
            <div className="result-header">
              <span className="success-icon">✅</span>
              <h3>Digest Generated Successfully</h3>
            </div>
            <div className="debug-section">
              <span className="label">Agent Request ID (Debug):</span>
              <code className="debug-id">{resultId}</code>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
