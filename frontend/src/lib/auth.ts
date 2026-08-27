import { writable } from 'svelte/store';
import { api, clearToken, getToken, setToken } from '$lib/api';

export interface User {
	id: number;
	email: string;
	full_name: string;
	created_at: string;
}

export const user = writable<User | null>(null);
export const authReady = writable(false);

export function isAuthenticated(): boolean {
	return getToken() !== null;
}

export async function loadUserFromStorage(): Promise<void> {
	if (!getToken()) {
		authReady.set(true);
		return;
	}
	try {
		const me = await api.get<User>('/auth/me');
		user.set(me);
	} catch {
		clearToken();
		user.set(null);
	} finally {
		authReady.set(true);
	}
}

export async function login(email: string, password: string): Promise<User> {
	const data = await api.post<{ access_token: string; user: User }>('/auth/login', {
		email,
		password
	});
	setToken(data.access_token);
	user.set(data.user);
	return data.user;
}

export async function register(fullName: string, email: string, password: string): Promise<User> {
	const data = await api.post<{ access_token: string; user: User }>('/auth/register', {
		full_name: fullName,
		email,
		password
	});
	setToken(data.access_token);
	user.set(data.user);
	return data.user;
}

export async function logout(): Promise<void> {
	try {
		await api.post('/auth/logout', {});
	} catch {
		/* ignore network errors during logout */
	}
	clearToken();
	user.set(null);
}
