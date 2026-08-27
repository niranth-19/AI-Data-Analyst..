<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import api, { ApiError } from '$lib/api';
	import DataTable from '$lib/components/DataTable.svelte';
	import type {
		CleanResponse,
		Dataset,
		PreviewResponse,
		QualityResponse,
		StatisticsResponse
	} from '$lib/types';

	const dataset_id = Number(page.params.id);

	let dataset: Dataset | null = $state(null);
	let tab: 'preview' | 'statistics' | 'quality' | 'clean' = $state('preview');

	let loading = $state(true);
	let error = $state('');

	let preview: PreviewResponse | null = $state(null);
	let stats: StatisticsResponse | null = $state(null);
	let quality: QualityResponse | null = $state(null);

	let cleanOptions = $state({
		drop_duplicates: true,
		fill_numeric_strategy: 'median',
		fill_categorical_strategy: 'mode',
		drop_empty_columns: true,
		trim_strings: true,
		convert_date_columns: true
	});
	let cleaning = $state(false);
	let cleanResult: CleanResponse | null = $state(null);
	let cleanError = $state('');

	async function loadPreview() {
		preview = await api.get<PreviewResponse>(`/datasets/${dataset_id}/preview`);
	}

	async function loadStats() {
		stats = await api.get<StatisticsResponse>(`/datasets/${dataset_id}/statistics`);
	}

	async function loadQuality() {
		quality = await api.get<QualityResponse>(`/datasets/${dataset_id}/quality`);
	}

	async function switchTab(next: 'preview' | 'statistics' | 'quality' | 'clean') {
		tab = next;
		if (tab === 'preview' && !preview) await loadPreview();
		if (tab === 'statistics' && !stats) await loadStats();
		if (tab === 'quality' && !quality) await loadQuality();
	}

	async function clean() {
		cleaning = true;
		cleanError = '';
		cleanResult = null;
		try {
			cleanResult = await api.post<CleanResponse>(`/datasets/${dataset_id}/clean`, cleanOptions);
			const d = await api.get<Dataset>(`/datasets/${dataset_id}`);
			dataset = d;
			preview = null;
			stats = null;
			quality = null;
		} catch (e) {
			cleanError = e instanceof ApiError ? e.message : 'Cleaning failed.';
		} finally {
			cleaning = false;
		}
	}

	async function generateReport() {
		try {
			await api.post('/reports', { dataset_id });
			goto('/reports');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Report generation failed.';
		}
	}

	async function deleteDataset() {
		if (!confirm('Delete this dataset and all its analyses and reports?')) return;
		try {
			await api.del(`/datasets/${dataset_id}`);
			goto('/dashboard');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Delete failed.';
		}
	}

	onMount(async () => {
		try {
			dataset = await api.get<Dataset>(`/datasets/${dataset_id}`);
			await loadPreview();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Could not load dataset.';
		} finally {
			loading = false;
		}
	});

	const severityBadge = (s: string) =>
		s === 'high' ? 'badge-red' : s === 'medium' ? 'badge-yellow' : 'badge-gray';
</script>

<svelte:head>
	<title>{dataset?.original_filename ?? 'Dataset'} — AI Data Analyst</title>
</svelte:head>

<div class="container page">
	{#if loading}
		<p class="muted"><span class="spinner"></span> Loading dataset...</p>
	{:else if error}
		<div class="error-box">{error}</div>
	{:else if dataset}
		<div class="head">
			<div>
				<a href="/dashboard" class="back">← Dashboard</a>
				<h1>{dataset.original_filename}</h1>
				<p class="muted">
					{dataset.row_count} rows × {dataset.column_count} columns ·
					<span class="badge badge-blue">{dataset.file_format.toUpperCase()}</span>
					<span class="badge {dataset.status === 'cleaned' ? 'badge-green' : 'badge-gray'}">
						{dataset.status}
					</span>
				</p>
			</div>
			<div class="head-actions">
				<a class="btn btn-primary" href={`/datasets/${dataset.id}/analyze`}>Ask AI</a>
				<button class="btn btn-secondary" onclick={generateReport}>PDF Report</button>
				<button class="btn btn-danger" onclick={deleteDataset}>Delete</button>
			</div>
		</div>

		<div class="tabs">
			{#each ['preview', 'statistics', 'quality', 'clean'] as t}
				<button class="tab" class:active={tab === t} onclick={() => switchTab(t as typeof tab)}>
					{t.charAt(0).toUpperCase() + t.slice(1)}
				</button>
			{/each}
		</div>

		{#if tab === 'preview'}
			<div class="card">
				<h2>Data Preview</h2>
				<p class="muted">Showing the first {preview?.total_rows_shown ?? 0} rows.</p>
				{#if preview}
					<DataTable columns={Object.keys(preview.rows[0] ?? {})} rows={preview.rows} />
				{/if}
			</div>
		{/if}

		{#if tab === 'statistics'}
			<div class="card">
				<h2>Statistics</h2>
				{#if stats}
					<table class="data-table">
						<thead>
							<tr>
								<th>Column</th>
								<th>Type</th>
								<th>Count</th>
								<th>Missing</th>
								<th>Unique</th>
								<th>Mean</th>
								<th>Median</th>
								<th>Min</th>
								<th>Max</th>
								<th>Sum</th>
								<th>Std</th>
							</tr>
						</thead>
						<tbody>
							{#each stats.columns as c}
								<tr>
									<td><b>{c.name}</b></td>
									<td class="muted">{c.dtype}</td>
									<td>{c.count}</td>
									<td>{c.missing}</td>
									<td>{c.unique}</td>
									<td>{c.numeric?.mean ?? '—'}</td>
									<td>{c.numeric?.median ?? '—'}</td>
									<td>{c.numeric?.min ?? '—'}</td>
									<td>{c.numeric?.max ?? '—'}</td>
									<td>{c.numeric?.sum ?? '—'}</td>
									<td>{c.numeric?.std ?? '—'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</div>
		{/if}

		{#if tab === 'quality'}
			<div class="card">
				<h2>Data Quality Analysis</h2>
				{#if quality}
					<div class="q-cards">
						<div class="q-card"><span class="q-num">{quality.total_cells}</span>Total cells</div>
						<div class="q-card"><span class="q-num">{quality.missing_cells}</span>Missing cells ({quality.missing_percent}%)</div>
						<div class="q-card"><span class="q-num">{quality.duplicate_rows}</span>Duplicate rows</div>
						<div class="q-card"><span class="q-num">{quality.empty_columns.length}</span>Empty columns</div>
					</div>

					{#if quality.issues.length > 0}
						<h3>Detected issues</h3>
						<div class="issues">
							{#each quality.issues as issue}
								<div class="issue">
									<span class="badge {severityBadge(issue.severity)}">{issue.severity}</span>
									<span>{issue.message}</span>
								</div>
							{/each}
						</div>
					{:else}
						<div class="success-box">No data quality issues detected.</div>
					{/if}

					<h3>Columns</h3>
					<table class="data-table">
						<thead>
							<tr>
								<th>Column</th>
								<th>Data Type</th>
								<th>Missing</th>
								<th>Unique</th>
							</tr>
						</thead>
						<tbody>
							{#each quality.columns as c}
								<tr>
									<td><b>{c.name}</b></td>
									<td class="muted">{c.dtype}</td>
									<td>{c.missing}</td>
									<td>{c.unique}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</div>
		{/if}

		{#if tab === 'clean'}
			<div class="grid-2">
				<div class="card">
					<h2>Data Cleaning</h2>
					<p class="muted">The original file is kept. A cleaned copy is used after applying these options.</p>
					<label class="check"><input type="checkbox" bind:checked={cleanOptions.drop_duplicates} /> Remove duplicate rows</label>
					<label class="check"><input type="checkbox" bind:checked={cleanOptions.drop_empty_columns} /> Drop empty columns</label>
					<label class="check"><input type="checkbox" bind:checked={cleanOptions.trim_strings} /> Trim whitespace in text</label>
					<label class="check"><input type="checkbox" bind:checked={cleanOptions.convert_date_columns} /> Convert date columns</label>
					<div class="field">
						<label class="label" for="fill-numeric">Missing numeric values</label>
						<select id="fill-numeric" class="input" bind:value={cleanOptions.fill_numeric_strategy}>
							<option value="median">Fill with median</option>
							<option value="mean">Fill with mean</option>
							<option value="mode">Fill with mode</option>
							<option value="drop">Drop rows with missing values</option>
							<option value="none">Leave as is</option>
						</select>
					</div>
					<div class="field">
						<label class="label" for="fill-cat">Missing text values</label>
						<select id="fill-cat" class="input" bind:value={cleanOptions.fill_categorical_strategy}>
							<option value="mode">Fill with most common value</option>
							<option value="drop">Drop rows with missing values</option>
							<option value="none">Leave as is</option>
						</select>
					</div>
					{#if cleanError}
						<div class="error-box">{cleanError}</div>
					{/if}
					<button class="btn btn-primary" onclick={clean} disabled={cleaning}>
						{#if cleaning}<span class="spinner"></span> Cleaning...{:else}Apply cleaning{/if}
					</button>
				</div>

				<div class="card">
					<h2>Result</h2>
					{#if cleanResult}
						<div class="success-box">{cleanResult.message}</div>
						<p class="muted">
							Rows: {cleanResult.rows_before} → <b>{cleanResult.rows_after}</b><br />
							Columns: {cleanResult.columns_before} → <b>{cleanResult.columns_after}</b>
						</p>
						<h3>Operations</h3>
						<ul>
							{#each cleanResult.operations as op}
								<li>{op}</li>
							{/each}
						</ul>
					{:else}
						<p class="muted">No cleaning has been applied yet.</p>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.page {
		padding: 24px 20px 40px;
	}

	.back {
		font-size: 13px;
	}

	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 16px;
		flex-wrap: wrap;
		margin-bottom: 16px;
	}

	.head h1 {
		margin: 4px 0;
		font-size: 26px;
		word-break: break-all;
	}

	.head-actions {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}

	.tabs {
		display: flex;
		gap: 4px;
		border-bottom: 2px solid var(--border);
		margin-bottom: 18px;
	}

	.tab {
		background: none;
		border: none;
		padding: 10px 18px;
		font-size: 14px;
		font-weight: 600;
		color: var(--muted);
		cursor: pointer;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
	}

	.tab.active {
		color: var(--primary);
		border-bottom-color: var(--primary);
	}

	.q-cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: 10px;
		margin-bottom: 18px;
	}

	.q-card {
		background: var(--primary-light);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 14px;
		font-size: 13px;
		color: var(--muted);
	}

	.q-num {
		display: block;
		font-size: 24px;
		font-weight: 700;
		color: var(--primary-dark);
	}

	.issues {
		display: flex;
		flex-direction: column;
		gap: 6px;
		margin-bottom: 18px;
	}

	.issue {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 12px;
		background: #f8fafc;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 13px;
	}

	h3 {
		margin: 18px 0 10px;
		font-size: 15px;
	}

	.check {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 0;
		font-size: 14px;
	}

	.field {
		margin-top: 12px;
	}
</style>