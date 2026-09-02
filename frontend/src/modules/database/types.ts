// Frontend models for the database operations page. The wire envelope is
// snake_case (project rule: only requests are converted on the way out), so
// `api/database.api.ts` maps it onto these camelCase shapes.

export type BackupFormat = "custom" | "sql";
export type BackupOrigin = "export" | "upload";
export type BackupStatus = "in_progress" | "completed" | "failed";

export interface DatabaseBackup {
  id: string;
  filename: string;
  /** Absolute path on the server filesystem — the database stores only this. */
  filePath: string;
  format: BackupFormat;
  origin: BackupOrigin;
  status: BackupStatus;
  sizeBytes: number;
  durationMs: number | null;
  error: string | null;
  createdBy: string | null;
  createdByName: string | null;
  createdAt: string;
  completedAt: string | null;
  restoredAt: string | null;
  restoredBy: string | null;
  restoredByName: string | null;
  /** "completed" | "failed" | null when this dump was never restored. */
  restoreStatus: "completed" | "failed" | null;
  restoreError: string | null;
  /** False when the file was removed from disk behind the registry's back. */
  fileExists: boolean;
}

export interface DatabaseStatus {
  name: string | null;
  host: string | null;
  port: number | null;
  serverVersion: string | null;
  sizeBytes: number | null;
  tableCount: number | null;
  reachable: boolean;
  error: string | null;
  /** Engine the server will use for the next export: pg_dump or plain SQL. */
  engine: BackupFormat;
  pgToolsAvailable: boolean;
  backupDir: string;
  backupCount: number;
  lastBackupAt: string | null;
  maxUploadMb: number;
}
