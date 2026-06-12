const publicApiBasePath = (import.meta.env.VITE_API_BASE_PATH?.trim() || '/api').replace(/\/$/, '');
const adminNamespace = import.meta.env.VITE_ADMIN_API_NAMESPACE?.trim() || 'workbench';
const adminApiBasePath = `${publicApiBasePath}/admin/${adminNamespace}`;
const bundledAdminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim();
const adminTokenStorageKey = 'issueAggregatorAdminToken';

async function parseResponse(response) {
    return response.json();
}
export function buildAdminApiPath(path) {
    return `${adminApiBasePath}${path.startsWith('/') ? path : `/${path}`}`;
}
export function buildPublicApiPath(path) {
    return `${publicApiBasePath}${path.startsWith('/') ? path : `/${path}`}`;
}
function getAdminToken() {
    if (bundledAdminToken) {
        return bundledAdminToken;
    }
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
function buildHeaders(path, includeJson = false) {
    const headers = includeJson ? { 'Content-Type': 'application/json' } : {};
    const adminToken = path.startsWith(adminApiBasePath) ? getAdminToken() : undefined;
    if (adminToken) {
        headers['X-Admin-Token'] = adminToken;
    }
    return headers;
}
export async function apiGet(path) {
    const response = await fetch(path, {
        headers: buildHeaders(path),
    });
    return parseResponse(response);
}
export async function apiPost(path, payload) {
    const response = await fetch(path, {
        method: 'POST',
        headers: buildHeaders(path, true),
        body: JSON.stringify(payload),
    });
    return parseResponse(response);
}
export async function apiPut(path, payload) {
    const response = await fetch(path, {
        method: 'PUT',
        headers: buildHeaders(path, true),
        body: JSON.stringify(payload),
    });
    return parseResponse(response);
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
