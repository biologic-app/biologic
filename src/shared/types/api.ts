interface BaseMeta {
  timestamp: string
  requestId: string | null
  version: string
}

interface OperationMeta extends BaseMeta {
  operation: string | null
}

interface IncludesMeta extends BaseMeta {
  includesRequested: string[]
  includesApplied: string[]
  includesAllowed: string[]
}

interface ApiDataResponse<T> {
  data: T
}

export interface ApiCommandResponse<T> extends ApiDataResponse<T> {
  meta: OperationMeta
}

export type ApiCreateResponse<T> = ApiCommandResponse<T>

export interface ApiReadResponse<T> extends ApiDataResponse<T> {
  meta: IncludesMeta & { includes: string[] }
}

export interface ApiViewResponse<T> {
  items: T[]
  meta: IncludesMeta & {
    total: number
    offset: number
    limit: number
  }
}

export type ApiUpdateResponse<T> = ApiCommandResponse<T>

export interface ApiDeleteResponse<T> extends ApiDataResponse<T> {
  meta: OperationMeta & { deleted: boolean }
}

export interface ValidationError {
  type: string
  loc: (string | number)[]
  msg: string
  input: unknown
  ctx?: Record<string, unknown>  
}

export type ErrorStatus =
  | 400 | 401 | 403 | 404 | 409 | 422 | 429 | 500 | 502 | 503
  | (number & {})

export type ErrorTitle =
  | "Validation failed"
  | "Unauthorized"
  | "Forbidden"
  | "Not Found"
  | "Conflict"
  | "Unprocessable Entity"
  | "Too Many Requests"
  | "Internal Server Error"
  | "Bad Gateway"
  | "Service Unavailable"
  | (string & {})

export interface ApiErrorResponse {
  type: string
  title: ErrorTitle
  status: ErrorStatus
  detail: string
  instance: string
  errors?: ValidationError[]
}

export interface ApiValidationError extends ApiErrorResponse {
  status: 422
  title: "Validation failed" | "Unprocessable Entity"
  errors: ValidationError[] 
}

export interface ApiError {
  status: number
  code?: string
  message: string
}

export function isValidationError(error: ApiErrorResponse): error is ApiValidationError {
  return error.status === 422 && Array.isArray(error.errors)
}

export function isApiError(value: unknown): value is ApiErrorResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    'title' in value
  )
}

export interface NamedRef {
  id: number | null
  name: string | null
}
