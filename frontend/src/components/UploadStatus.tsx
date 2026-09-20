interface UploadStatusProps {
  uploading: boolean;
  progress: number;
  error: string | null;
}

export function UploadStatus({
  uploading,
  progress,
  error,
}: UploadStatusProps) {
  return (
    <div className="upload-status">
      {uploading && <p className="muted">Téléversement… {progress}%</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
