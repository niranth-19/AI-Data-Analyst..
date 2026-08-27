const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api';

export class ApiError extends Error {
	status: number;

	constructor(status: number, message: string) {
		super(message);
		this.status = status;
	}
}

const TOKEN_KEY = 'ai_data_analyst_token';

export function getToken(): string | null {
	return typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
}

export function setToken(token: string): void {
	localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
	localStorage.removeItem(TOKEN_KEY);
}

function extractDetail(data: unknown, status: number): string {
	if (data && typeof data === 'object') {
		const d = data as { detail?: unknown };
		if (typeof d.detail === 'string') return d.detail;
		if (Array.isArray(d.detail)) {
			const first = d.detail[0] as { msg?: string };
			if (first && typeof first.msg === 'string') return first.msg;
		}
	}
	return `Request failed with status ${status}.`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const headers = new Headers(options.headers ?? {});
	headers.set('Accept', 'application/json');
	const token = getToken();
	if (token) headers.set('Authorization', `Bearer ${token}`);

	const isForm = options.body instanceof FormData;
	if (!isForm && options.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}

	const res = await fetch(API_BASE + path, { ...options, headers });
	if (!res.ok) {
		let message = `Request failed with status ${res.status}.`;
		try {
			const data = await res.json();
			message = extractDetail(data, res.status);
		} catch {
			/* ignore parse errors */
		}
		if (res.status === 401) {
			clearToken();
		}
		throw new ApiError(res.status, message);
	}
	if (res.status === 204) return undefined as T;
	return (await res.json()) as T;
}

export const api = {
	get: <T>(path: string) => request<T>(path),
	post: <T>(path: string, body?: unknown) =>
		request<T>(path, {
			method: 'POST',
			body: body instanceof FormData ? body : JSON.stringify(body ?? {})
		}),
	del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
	downloadUrl: (path: string) => {
		const sep = path.startsWith('/') ? '' : '/';
		return API_BASE + sep + path;
	},
	getDownload: async (path: string, filename: string) => {
		const res = await fetch(API_BASE + path, {
			headers: { Authorization: `Bearer ${getToken() ?? ''}` }
		});
		if (!res.ok) throw new ApiError(res.status, 'Failed to download file.');
		const blob = await res.blob();
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		a.remove();
		URL.revokeObjectURL(url);
	}
};

export default api;
