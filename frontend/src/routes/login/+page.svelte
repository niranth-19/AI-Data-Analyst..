<script lang="ts">
	import { goto } from '$app/navigation';
	import { login } from '$lib/auth';
	import { ApiError } from '$lib/api';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submit() {
		if (busy) return;
		error = '';
		busy = true;
		try {
			await login(email.trim(), password);
			goto('/dashboard');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Login failed. Please try again.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>Log in — AI Data Analyst</title>
</svelte:head>

<div class="auth-wrap">
	<div class="card auth-card">
		<h1>Welcome back</h1>
		<p class="muted">Log in to access your datasets and analyses.</p>

		{#if error}
			<div class="error-box">{error}</div>
		{/if}

		<form onsubmit={(e) => { e.preventDefault(); submit(); }}>
			<div class="field">
				<label class="label" for="email">Email</label>
				<input id="email" class="input" type="email" bind:value={email} required autocomplete="email" />
			</div>
			<div class="field">
				<label class="label" for="password">Password</label>
				<input
					id="password"
					class="input"
					type="password"
					bind:value={password}
					required
					autocomplete="current-password"
				/>
			</div>
			<button class="btn btn-primary btn-block" type="submit" disabled={busy}>
				{#if busy}<span class="spinner"></span>{:else}Log in{/if}
			</button>
		</form>

		<p class="muted switch">
			Don't have an account? <a href="/register">Create one</a>
		</p>
	</div>
</div>

<style>
	.auth-wrap {
		min-height: calc(100vh - 60px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 40px 20px;
	}

	.auth-card {
		width: 100%;
		max-width: 400px;
	}

	.auth-card h1 {
		margin: 0 0 4px;
		font-size: 26px;
	}

	.field {
		margin-bottom: 14px;
	}

	.btn-block {
		width: 100%;
		margin-top: 6px;
	}

	.switch {
		margin-top: 16px;
		text-align: center;
		font-size: 14px;
	}
</style>