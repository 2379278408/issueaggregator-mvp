export type ApiEnvelope<T> = {
  success: boolean
  data: T
  error_code?: string
  message?: string
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

async function parseResponse<T>(response: Response): Promise<ApiEnvelope<T>> {
  return response.json() as Promise<ApiEnvelope<T>>
}

export async function apiGet<T>(path: string): Promise<ApiEnvelope<T>> {
  const response = await fetch(path)
  return parseResponse<T>(response)
}

export async function apiPost<TResponse, TPayload>(path: string, payload: TPayload): Promise<ApiEnvelope<TResponse>> {
  const response = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return parseResponse<TResponse>(response)
}

export async function apiPut<TResponse, TPayload>(path: string, payload: TPayload): Promise<ApiEnvelope<TResponse>> {
  const response = await fetch(path, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return parseResponse<TResponse>(response)
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
  return query ? `/api/issues/submitted/search?${query}` : '/api/issues/submitted'
}
