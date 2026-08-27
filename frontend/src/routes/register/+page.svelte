<script lang="ts">
	import { goto } from '$app/navigation';
	import { register } from '$lib/auth';
	import { ApiError } from '$lib/api';

	let fullName = $state('');
	let email = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submit() {
		if (busy) return;
		error = '';
		if (password.length < 8) {
			error = 'Password must be at least 8 characters.';
			return;
		}
		busy = true;
		try {
			await register(fullName.trim(), email.trim(), password);
			goto('/dashboard');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Registration failed. Please try again.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>Create account — AI Data Analyst</title>
</svelte:head>

<div class="auth-wrap">
	<div class="card auth-card">
		<h1>Create your account</h1>
		<p class="muted">Start analyzing your data with AI.</p>

		{#if error}
			<div class="error-box">{error}</div>
		{/if}

		<form onsubmit={(e) => { e.preventDefault(); submit(); }}>
			<div class="field">
				<label class="label" for="name">Full name</label>
				<input id="name" class="input" type="text" bind:value={fullName} required minlength="2" />
			</div>
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
					minlength="8"
					autocomplete="new-password"
				/>
				<span class="muted hint">At least 8 characters, with letters and digits.</span>
			</div>
			<button class="btn btn-primary btn-block" type="submit" disabled={busy}>
				{#if busy}<span class="spinner"></span>{:else}Create account{/if}
			</button>
		</form>

		<p class="muted switch">
			Already have an account? <a href="/login">Log in</a>
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

	.hint {
		display: block;
		font-size: 12px;
		margin-top: 4px;
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