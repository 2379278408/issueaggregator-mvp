const publicApiBasePath = (import.meta.env.VITE_API_BASE_PATH?.trim() || '/api').replace(/\/$/, '');
const adminNamespace = import.meta.env.VITE_ADMIN_API_NAMESPACE?.trim() || 'workbench';
const adminApiBasePath = `${publicApiBasePath}/admin/${adminNamespace}`;
const adminTokenStorageKey = 'issueAggregatorAdminToken';

async function parseResponse(response) {
    try {
        return {
            ...await response.json(),
            http_status: response.status,
        };
    }
    catch {
        return {
            success: false,
            data: null,
            error_code: 'INVALID_API_RESPONSE',
            message: response.ok ? '接口返回格式异常' : `接口请求失败：HTTP ${response.status}`,
            http_status: response.status,
        };
    }
}
async function requestApi(input, init) {
    try {
        const response = await fetch(input, init);
        return parseResponse(response);
    }
    catch {
        return {
            success: false,
            data: null,
            error_code: 'NETWORK_ERROR',
            message: '网络连接失败，请稍后重试',
        };
    }
}
export function buildAdminApiPath(path) {
    return `${adminApiBasePath}${path.startsWith('/') ? path : `/${path}`}`;
}
export function buildPublicApiPath(path) {
    return `${publicApiBasePath}${path.startsWith('/') ? path : `/${path}`}`;
}
function getAdminToken() {
    if (typeof window === 'undefined') {
        return undefined;
    }
    return window.sessionStorage.getItem(adminTokenStorageKey)?.trim() || undefined;
}
export function hasAdminToken() {
    return Boolean(getAdminToken());
}
export function setAdminToken(token) {
    if (typeof window === 'undefined') {
        return;
    }
    window.sessionStorage.setItem(adminTokenStorageKey, token.trim());
}
export function clearAdminToken() {
    if (typeof window === 'undefined') {
        return;
    }
    window.sessionStorage.removeItem(adminTokenStorageKey);
}
function buildHeaders(path, includeJson = false) {
    const headers = includeJson ? { 'Content-Type': 'application/json' } : {};
    const isAdminApiPath = path === adminApiBasePath || path.startsWith(`${adminApiBasePath}/`) || path.startsWith(`${adminApiBasePath}?`);
    const adminToken = isAdminApiPath ? getAdminToken() : undefined;
    if (adminToken) {
        headers['X-Admin-Token'] = adminToken;
    }
    return headers;
}
export async function apiGet(path) {
    return requestApi(path, {
        headers: buildHeaders(path),
    });
}
export async function apiPost(path, payload) {
    return requestApi(path, {
        method: 'POST',
        headers: buildHeaders(path, true),
        body: JSON.stringify(payload),
    });
}
export async function apiPut(path, payload) {
    return requestApi(path, {
        method: 'PUT',
        headers: buildHeaders(path, true),
        body: JSON.stringify(payload),
    });
}
export function buildSubmittedIssueSearch(params) {
    const searchParams = new URLSearchParams();
    if (params.related_id) {
        searchParams.set('related_id', params.related_id);
    }
    if (params.type && params.type !== 'all') {
        searchParams.set('type', params.type);
    }
    if (params.keyword) {
        searchParams.set('keyword', params.keyword);
    }
    const query = searchParams.toString();
    const submittedIssuesPath = buildPublicApiPath('/issues/submitted');
    return query ? `${submittedIssuesPath}/search?${query}` : submittedIssuesPath;
}
