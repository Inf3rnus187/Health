import { useState } from 'react';
import type { ChangeEvent } from 'react';

import { useResetImported } from '../hooks/useResetImported';
import { useUploadExport } from '../hooks/useUploadExport';
import { UploadControls } from './UploadControls';
import { UploadStatus } from './UploadStatus';

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const { mutation, progress } = useUploadExport();
  const reset = useResetImported();
  const onFile = (event: ChangeEvent<HTMLInputElement>) =>
    setFile(event.target.files?.[0] ?? null);
  return (
    <>
      <UploadControls
        canImport={file !== null}
        uploading={mutation.isPending}
        resetting={reset.isPending}
        onFile={onFile}
        onImport={() => file && mutation.mutate(file)}
        onReset={() => reset.mutate()}
      />
      <UploadStatus
        uploading={mutation.isPending}
        progress={progress}
        error={mutation.isError ? (mutation.error as Error).message : null}
      />
    </>
  );
}
