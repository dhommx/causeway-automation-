import createClient from "openapi-fetch";

import type { components, paths } from "./api-types";

/** Typed client for the backend. Types come from `pnpm gen:api` (backend must be running). */
export const api = createClient<paths>({ baseUrl: "" });

export type Schemas = components["schemas"];
export type Workflow = Schemas["WorkflowOut"];
export type Department = Schemas["DepartmentOut"];
export type StoredFile = Schemas["StoredFileOut"];
export type Preview = Schemas["PreviewOut"];
export type Run = Schemas["RunOut"];
export type RuleSet = Schemas["RuleSetOut"];
export type AuditEvent = Schemas["AuditEventOut"];

/** Turns an API error body into a message for the user. */
export function errorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (!error) return fallback;
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  const detail = (error as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return fallback;
}

/** Unwraps an openapi-fetch result: returns data or throws a readable Error. */
export function unwrap<T>(result: { data?: T; error?: unknown }): T {
  if (result.error !== undefined || result.data === undefined) {
    throw new Error(errorMessage(result.error));
  }
  return result.data;
}

export const downloadUrl = (fileId: string) => `/api/v1/files/${fileId}/download`;
/** URL the browser can display directly (used for images). */
export const viewUrl = (fileId: string) => `/api/v1/files/${fileId}/download?inline=true`;

const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "gif", "bmp"];
export const isImage = (name: string) => IMAGE_EXTENSIONS.includes(name.split(".").pop()?.toLowerCase() ?? "");
