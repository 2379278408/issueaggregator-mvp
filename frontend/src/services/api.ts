export type ApiEnvelope<T> = {
  success: boolean
  data: T
  error_code?: string
  message?: string
  http_status?: number
}

export type SubmittedIssue = {
  issue_number: number
  title: string
  issue_url: string
  related_id: string
  type: string
  submitted_at: string
}

export type FeedbackItem = {
  id: string
  type: string
  related_id: string
  raw_content: string
  expected_behavior?: string | null
  actual_behavior?: string | null
  status: string
  created_at: string
  submitted_at?: string | null
  batch_id?: string | null
  batch_status?: string | null
  batch_integration_error?: string | null
  draft_id?: string | null
  draft_status?: string | null
}

export type AuditEventRecord = {
  id: string
  event_type: string
  client_ip: string
  path: string
  action?: string | null
  resource_id?: string | null
  created_at: string
}

export type PaginatedResponse<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
}

export type FeedbackCreatePayload = {
  type: string
  related_id: string
  raw_content: string
  expected_behavior?: string
  actual_behavior?: string
}

export type DraftBatchCreatePayload = {
  feedback_item_ids: string[]
  confirm_mixed_related_ids: boolean
}

export type DraftBatchCreateResponse = {
  id: string
  status: string
  primary_related_id: string | null
  related_id_count: number
  created_at: string
}

export type DraftIntegrateResponse = {
  batch_id: string
  draft_id: string
  status: string
}

export type DraftRecord = {
  id: string
  batch_id: string
  title: string
  body_markdown: string
  related_id_summary: string
  status: string
  ai_model?: string | null
  prompt_snapshot?: string | null
  updated_at: string
}

export type DraftUpdatePayload = {
  title: string
  body_markdown: string
}

export type DraftSubmitResponse = {
  draft_id: string
  issue_number: number
  issue_url: string
  related_id: string
  submitted_at: string
}

const publicApiBasePath = ((import.meta.env.VITE_API_BASE_PATH as string | undefined)?.trim() || '/api').replace(/\/$/, '')
const adminNamespace = (import.meta.env.VITE_ADMIN_API_NAMESPACE as string | undefined)?.trim() || 'workbench'
const adminApiBasePath = `${publicApiBasePath}/admin/${adminNamespace}`
const adminTokenStorageKey = 'issueAggregatorAdminToken'

async function parseResponse<T>(response: Response): Promise<ApiEnvelope<T>> {
  try {
    return {
      ...((await response.json()) as ApiEnvelope<T>),
      http_status: response.status,
    }
  } catch {
    return {
      success: false,
      data: null as T,
      error_code: 'INVALID_API_RESPONSE',
      message: response.ok ? '接口返回格式异常' : `接口请求失败：HTTP ${response.status}`,
      http_status: response.status,
    }
  }
}

async function requestApi<T>(input: string, init: RequestInit): Promise<ApiEnvelope<T>> {
  try {
    const response = await fetch(input, init)
    return parseResponse<T>(response)
  } catch {
    return {
      success: false,
      data: null as T,
      error_code: 'NETWORK_ERROR',
      message: '网络连接失败，请稍后重试',
    }
  }
}

export function buildAdminApiPath(path: string): string {
  return `${adminApiBasePath}${path.startsWith('/') ? path : `/${path}`}`
}

export function buildPublicApiPath(path: string): string {
  return `${publicApiBasePath}${path.startsWith('/') ? path : `/${path}`}`
}

function getAdminToken(): string | undefined {
  if (typeof window === 'undefined') {
    return undefined
  }
  return window.sessionStorage.getItem(adminTokenStorageKey)?.trim() || undefined
}

export function hasAdminToken(): boolean {
  return Boolean(getAdminToken())
}

export function setAdminToken(token: string): void {
  if (typeof window === 'undefined') {
    return
  }
  window.sessionStorage.setItem(adminTokenStorageKey, token.trim())
}

export function clearAdminToken(): void {
  if (typeof window === 'undefined') {
    return
  }
  window.sessionStorage.removeItem(adminTokenStorageKey)
}

function buildHeaders(path: string, includeJson = false): HeadersInit {
  const headers: Record<string, string> = includeJson ? { 'Content-Type': 'application/json' } : {}
  const isAdminApiPath = path === adminApiBasePath || path.startsWith(`${adminApiBasePath}/`) || path.startsWith(`${adminApiBasePath}?`)
  const adminToken = isAdminApiPath ? getAdminToken() : undefined
  if (adminToken) {
    headers['X-Admin-Token'] = adminToken
  }
  return headers
}

export async function apiGet<T>(path: string): Promise<ApiEnvelope<T>> {
  return requestApi<T>(path, {
    headers: buildHeaders(path),
  })
}

export async function apiPost<TResponse, TPayload>(path: string, payload: TPayload): Promise<ApiEnvelope<TResponse>> {
  return requestApi<TResponse>(path, {
    method: 'POST',
    headers: buildHeaders(path, true),
    body: JSON.stringify(payload),
  })
}

export async function apiPut<TResponse, TPayload>(path: string, payload: TPayload): Promise<ApiEnvelope<TResponse>> {
  return requestApi<TResponse>(path, {
    method: 'PUT',
    headers: buildHeaders(path, true),
    body: JSON.stringify(payload),
  })
}

export function buildSubmittedIssueSearch(params: {
  related_id?: string
  type?: string
  keyword?: string
}): string {
  const searchParams = new URLSearchParams()

  if (params.related_id) {
    searchParams.set('related_id', params.related_id)
  }
  if (params.type && params.type !== 'all') {
    searchParams.set('type', params.type)
  }
  if (params.keyword) {
    searchParams.set('keyword', params.keyword)
  }

  const query = searchParams.toString()
  const submittedIssuesPath = buildPublicApiPath('/issues/submitted')
  return query ? `${submittedIssuesPath}/search?${query}` : submittedIssuesPath
}
