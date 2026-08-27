<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import api, { ApiError } from '$lib/api';
	import { user } from '$lib/auth';
	import type { Dataset } from '$lib/types';

	let datasets: Dataset[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let uploading = $state(false);
	let uploadError = $state('');
	let uploadSuccess = $state('');

	async function load() {
		loading = true;
		error = '';
		try {
			const res = await api.get<{ datasets: Dataset[]; total: number }>('/datasets');
			datasets = res.datasets;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Could not load datasets.';
		} finally {
			loading = false;
		}
	}

	async function onFileSelected(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		uploading = true;
		uploadError = '';
		uploadSuccess = '';
		const form = new FormData();
		form.append('file', file);
		try {
			const res = await api.post<{ dataset: Dataset }>('/datasets/upload', form);
			uploadSuccess = `Uploaded "${res.dataset.original_filename}" (${res.dataset.row_count} rows).`;
			await load();
			input.value = '';
		} catch (err) {
			uploadError = err instanceof ApiError ? err.message : 'Upload failed.';
		} finally {
			uploading = false;
		}
	}

	function fmtSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	onMount(load);
</script>

<svelte:head>
	<title>Dashboard — AI Data Analyst</title>
</svelte:head>

<div class="container page">
	<h1>Dashboard</h1>
	<p class="muted">Welcome back, {$user?.full_name}. Upload a dataset to get started.</p>

	<div class="card upload-card">
		<h2>Upload a dataset</h2>
		<p class="muted">Supported formats: CSV, XLSX, XLS. Maximum size: 20 MB.</p>
		<label class="drop-zone" for="file-input" class:busy={uploading}>
			{#if uploading}
				<span class="spinner"></span>
				<span>Processing file...</span>
			{:else}
				<span class="drop-title">Click to choose a file or drag it here</span>
				<span class="muted">Your file is processed server-side and never sent to the AI wholesale.</span>
			{/if}
			<input id="file-input" type="file" accept=".csv,.xlsx,.xls" hidden onchange={onFileSelected} />
		</label>
		{#if uploadError}
			<div class="error-box">{uploadError}</div>
		{/if}
		{#if uploadSuccess}
			<div class="success-box">{uploadSuccess}</div>
		{/if}
	</div>

	<div class="card">
		<div class="section-head">
			<h2>Your datasets</h2>
			<span class="muted">{datasets.length} total</span>
		</div>

		{#if loading}
			<p class="muted"><span class="spinner"></span> Loading datasets...</p>
		{:else if error}
			<div class="error-box">{error}</div>
		{:else if datasets.length === 0}
			<p class="muted empty">No datasets yet. Upload a CSV or Excel file above to begin.</p>
		{:else}
			<div class="dataset-grid">
				{#each datasets as ds}
					<button class="card dataset-card" onclick={() => goto(`/datasets/${ds.id}`)}>
						<div class="dc-head">
							<span class="badge badge-blue">{ds.file_format.toUpperCase()}</span>
							<span class="badge {ds.status === 'cleaned' ? 'badge-green' : 'badge-gray'}">
								{ds.status}
							</span>
						</div>
						<h3 class="dc-name" title={ds.original_filename}>{ds.original_filename}</h3>
						<p class="muted">
							{ds.row_count} rows × {ds.column_count} columns · {fmtSize(ds.file_size_bytes)}
						</p>
						<p class="muted small">Uploaded {new Date(ds.created_at).toLocaleString()}</p>
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.page {
		padding: 28px 20px;
	}

	.page h1 {
		margin: 0 0 4px;
		font-size: 28px;
	}

	.upload-card {
		margin: 20px 0;
	}

	.upload-card h2 {
		margin: 0 0 4px;
		font-size: 18px;
	}

	.drop-zone {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		border: 2px dashed var(--border);
		border-radius: 10px;
		padding: 32px 20px;
		margin-top: 14px;
		cursor: pointer;
		text-align: center;
		transition: border-color 0.15s ease, background 0.15s ease;
	}

	.drop-zone:hover {
		border-color: var(--primary);
		background: var(--primary-light);
	}

	.drop-zone.busy {
		pointer-events: none;
		opacity: 0.7;
	}

	.drop-title {
		font-weight: 600;
		font-size: 15px;
	}

	.section-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}

	.section-head h2 {
		margin: 0;
		font-size: 18px;
	}

	.empty {
		padding: 24px 0;
	}

	.dataset-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
		gap: 14px;
	}

	.dataset-card {
		text-align: left;
		cursor: pointer;
		font-family: inherit;
		width: 100%;
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}

	.dataset-card:hover {
		border-color: var(--primary);
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
	}

	.dc-head {
		display: flex;
		gap: 8px;
		margin-bottom: 8px;
	}

	.dc-name {
		margin: 0 0 6px;
		font-size: 16px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.small {
		font-size: 12px;
		margin: 2px 0;
	}
</style>