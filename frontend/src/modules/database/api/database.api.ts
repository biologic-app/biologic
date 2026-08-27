// Database operations API — full-database export, upload and restore.
//
// The dump payload never travels through the database: the backend writes it to
// a file under APP_DATABASE_BACKUP_DIR and stores only the path, so every call
// here moves metadata except `downloadBackup`, which streams the file itself.

import {
  apiCommandRequest,
  apiCreateRequest,
  apiDeleteRequest,
  apiReadListRequest,
  apiReadRequest,
  buildApiUrl,
} from "@/shared/api/client.api";
import type {
  BackupFormat,
  BackupOrigin,
  BackupStatus,
  DatabaseBackup,
  DatabaseStatus,
} from "@/modules/database/types";

// A restore replaces every application table, so the backend refuses anything
// but this literal — the UI must spell it out rather than pass a boolean.
const RESTORE_CONFIRMATION = "RESTORE_DATABASE";

interface WireBackup {
  id: string;
  filename: string;
  file_path: string;
  format: BackupFormat;
  origin: BackupOrigin;
  status: BackupStatus;
  size_bytes: number;
  duration_ms: number | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
  restored_at: string | null;
  file_exists: boolean;
}

interface WireStatus {
  name?: string | null;
  host?: string | null;
  port?: number | null;
  server_version?: string | null;
  size_bytes?: number | null;
  table_count?: number | null;
  reachable: boolean;
  error: string | null;
  engine: BackupFormat;
  pg_tools_available: boolean;
  backup_dir: string;
  backup_count: number;
  last_backup_at: string | null;
  max_upload_mb: number;
}

const toBackup = (wire: WireBackup): DatabaseBackup => ({
  id: wire.id,
  filename: wire.filename,
  filePath: wire.file_path,
  format: wire.format,
  origin: wire.origin,
  status: wire.status,
  sizeBytes: wire.size_bytes,
  durationMs: wire.duration_ms,
  error: wire.error,
  createdAt: wire.created_at,
  completedAt: wire.completed_at,
  restoredAt: wire.restored_at,
  fileExists: wire.file_exists,
});

const toStatus = (wire: WireStatus): DatabaseStatus => ({
  name: wire.name ?? null,
  host: wire.host ?? null,
  port: wire.port ?? null,
  serverVersion: wire.server_version ?? null,
  sizeBytes: wire.size_bytes ?? null,
  tableCount: wire.table_count ?? null,
  reachable: wire.reachable,
  error: wire.error,
  engine: wire.engine,
  pgToolsAvailable: wire.pg_tools_available,
  backupDir: wire.backup_dir,
  backupCount: wire.backup_count,
  lastBackupAt: wire.last_backup_at,
  maxUploadMb: wire.max_upload_mb,
});

export async function fetchDatabaseStatus(): Promise<DatabaseStatus> {
  const response = await apiReadRequest<WireStatus>("/database/status");
  return toStatus(response.data);
}

export async function fetchBackups(): Promise<DatabaseBackup[]> {
  const response = await apiReadListRequest<WireBackup>("/database/backups");
  return (response.items ?? []).map(toBackup);
}

export async function createBackup(): Promise<DatabaseBackup> {
  const response = await apiCreateRequest<WireBackup>("/database/backups", { method: "POST" });
  return toBackup(response.data);
}

export async function uploadBackup(file: File): Promise<DatabaseBackup> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiCreateRequest<WireBackup>("/database/backups/upload", {
    method: "POST",
    body: formData,
  });
  return toBackup(response.data);
}

export async function restoreBackup(backupId: string): Promise<void> {
  await apiCommandRequest<{ id: string; restored_at: string }>(
    `/database/backups/${backupId}/restore`,
    { method: "POST", params: { confirmation: RESTORE_CONFIRMATION } },
  );
}

export async function deleteBackup(backupId: string): Promise<void> {
  await apiDeleteRequest<null>(`/database/backups/${backupId}`, { method: "DELETE" });
}

export async function downloadBackup(backup: DatabaseBackup): Promise<void> {
  // Streamed straight from the filesystem, so this bypasses the JSON client and
  // hands the browser a blob to save under the dump's own name.
  const response = await fetch(buildApiUrl(`/database/backups/${backup.id}/download`), {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = backup.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
