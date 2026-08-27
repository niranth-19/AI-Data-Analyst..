<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { user, logout } from '$lib/auth';

	let busy = $state(false);

	async function handleLogout() {
		if (busy) return;
		busy = true;
		await logout();
		busy = false;
		goto('/login');
	}
</script>

<nav class="nav">
	<div class="nav-inner">
		<a href="/" class="brand" onclick={() => goto('/')}>
			<span class="logo">AI</span>
			<span>AI Data Analyst</span>
		</a>

		{#if $user}
			<div class="links">
				<a href="/dashboard" class:active={page.url.pathname === '/dashboard'}>Dashboard</a>
				<a href="/history" class:active={page.url.pathname.startsWith('/history')}>History</a>
				<a href="/reports" class:active={page.url.pathname.startsWith('/reports')}>Reports</a>
			</div>
			<div class="user-area">
				<span class="user-name" title={$user.email}>{$user.full_name}</span>
				<button class="btn btn-secondary" onclick={handleLogout} disabled={busy}>Logout</button>
			</div>
		{:else}
			<div class="links">
				<a href="/login">Login</a>
				<a href="/register" class="btn btn-primary" style="padding:7px 14px;">Register</a>
			</div>
		{/if}
	</div>
</nav>

<style>
	.nav {
		background: var(--surface);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: 0;
		z-index: 50;
	}

	.nav-inner {
		max-width: 1100px;
		margin: 0 auto;
		padding: 10px 20px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		flex-wrap: wrap;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 8px;
		font-weight: 700;
		font-size: 16px;
		color: var(--text);
	}

	.brand:hover {
		text-decoration: none;
	}

	.logo {
		background: var(--primary);
		color: #fff;
		width: 28px;
		height: 28px;
		border-radius: 7px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 12px;
		font-weight: 800;
	}

	.links {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	.links a {
		color: var(--muted);
		font-weight: 500;
		font-size: 14px;
	}

	.links a:hover {
		color: var(--primary);
	}

	.links a.active {
		color: var(--primary);
		font-weight: 600;
	}

	.user-area {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.user-name {
		font-size: 14px;
		font-weight: 600;
	}
</style>
