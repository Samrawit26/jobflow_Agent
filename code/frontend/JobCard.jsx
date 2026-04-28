import { useState } from "react";

const API_BASE = "http://localhost:8000";

export default function JobCard({ job }) {
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);

  async function handleApply() {
    setStatus("loading");
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/apply/${job.id}`, {
        method: "POST",
      });

      if (!res.ok) throw new Error("Server error");

      const data = await res.json();
      setResult(data.application);
      setStatus("success");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>{job.title}</h2>
      <p style={styles.company}>{job.company}</p>

      {status === "idle" && (
        <button style={styles.button} onClick={handleApply}>
          Auto Apply
        </button>
      )}

      {status === "loading" && (
        <div style={styles.loading}>
          <span style={styles.spinner} />
          Submitting application...
        </div>
      )}

      {status === "success" && result && (
        <div style={styles.successCard}>
          <p style={styles.successTitle}>Application Submitted</p>
          <p><strong>Name:</strong> {result.candidate.name}</p>
          <p><strong>Email:</strong> {result.candidate.email}</p>
          <p><strong>Skills:</strong> {result.candidate.skills.join(", ") || "—"}</p>
          <p><strong>Status:</strong> {result.status}</p>
          <p><strong>Applied at:</strong> {new Date(result.applied_at).toLocaleString()}</p>
        </div>
      )}

      {status === "error" && (
        <p style={styles.error}>Something went wrong. Please try again.</p>
      )}
    </div>
  );
}

const styles = {
  card: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: 24,
    maxWidth: 420,
    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
    fontFamily: "system-ui, sans-serif",
  },
  title: {
    margin: "0 0 4px",
    fontSize: 18,
    fontWeight: 700,
    color: "#1a202c",
  },
  company: {
    margin: "0 0 16px",
    color: "#718096",
    fontSize: 14,
  },
  button: {
    background: "#4f46e5",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    padding: "10px 20px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  loading: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    color: "#4f46e5",
    fontSize: 14,
    fontWeight: 500,
  },
  spinner: {
    display: "inline-block",
    width: 16,
    height: 16,
    border: "2px solid #c7d2fe",
    borderTop: "2px solid #4f46e5",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  successCard: {
    background: "#f0fdf4",
    border: "1px solid #bbf7d0",
    borderRadius: 8,
    padding: 16,
    fontSize: 14,
    color: "#166534",
    lineHeight: 1.7,
  },
  successTitle: {
    fontWeight: 700,
    fontSize: 15,
    marginBottom: 8,
    color: "#15803d",
  },
  error: {
    color: "#dc2626",
    fontSize: 14,
  },
};
