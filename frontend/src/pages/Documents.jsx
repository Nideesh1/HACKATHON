import { useState, useEffect, useRef } from 'react'
import './Documents.css'

const API_BASE = 'http://localhost:8000'

function Documents() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [deleteModal, setDeleteModal] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    fetchDocuments()
  }, [])

  const fetchDocuments = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/documents`)
      if (!res.ok) throw new Error('Failed to fetch documents')
      const data = await res.json()
      setDocuments(data.documents)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    if (!file.name.endsWith('.txt')) {
      setError('Only .txt files are allowed')
      return
    }

    try {
      setUploading(true)
      setError(null)
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_BASE}/documents`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }

      await fetchDocuments()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDelete = async (docId) => {
    try {
      setError(null)
      setDeleteModal(null)
      const res = await fetch(`${API_BASE}/documents/${docId}`, {
        method: 'DELETE',
      })

      if (!res.ok) throw new Error('Delete failed')
      await fetchDocuments()
    } catch (err) {
      setError(err.message)
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="documents-page">
      <div className="page-header">
        <div className="header-row">
          <div>
            <h1>Documents</h1>
            <p>Medical claim documents for RAG queries</p>
          </div>
          <div className="upload-btn-wrapper">
            <input
              type="file"
              accept=".txt"
              onChange={handleUpload}
              ref={fileInputRef}
              id="file-upload"
              hidden
            />
            <label htmlFor="file-upload" className="btn btn-primary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              {uploading ? 'Uploading...' : 'Upload .txt'}
            </label>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      <div className="documents-section">
        {loading ? (
          <div className="loading">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="empty-state card">
            <div className="empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <p>No documents yet</p>
            <span>Upload .txt files to get started</span>
          </div>
        ) : (
          <div className="documents-list">
            <div className="list-header">
              <span className="col-name">Name</span>
              <span className="col-size">Size</span>
              <span className="col-chunks">Chunks</span>
              <span className="col-date">Uploaded</span>
              <span className="col-action"></span>
            </div>
            {documents.map((doc) => (
              <div key={doc.id} className="document-row">
                <div className="col-name">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span className="filename">{doc.filename}</span>
                </div>
                <span className="col-size">{formatSize(doc.size_bytes)}</span>
                <span className="col-chunks">{doc.chunk_count}</span>
                <span className="col-date">{formatDate(doc.uploaded_at)}</span>
                <div className="col-action">
                  <button
                    className="delete-btn"
                    onClick={() => setDeleteModal(doc)}
                    title="Delete document"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {deleteModal && (
        <div className="modal-overlay" onClick={() => setDeleteModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Delete Document</h3>
            <p>Are you sure you want to delete <strong>{deleteModal.filename}</strong>?</p>
            <p className="modal-hint">This will remove the document and its embeddings from the index.</p>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setDeleteModal(null)}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={() => handleDelete(deleteModal.id)}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Documents
