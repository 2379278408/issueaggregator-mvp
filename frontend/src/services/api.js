async function parseResponse(response) {
    return response.json();
}
export async function apiGet(path) {
    const response = await fetch(path);
    return parseResponse(response);
}
export async function apiPost(path, payload) {
    const response = await fetch(path, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });
    return parseResponse(response);
}
export async function apiPut(path, payload) {
    const response = await fetch(path, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
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
    return query ? `/api/issues/submitted/search?${query}` : '/api/issues/submitted';
}
