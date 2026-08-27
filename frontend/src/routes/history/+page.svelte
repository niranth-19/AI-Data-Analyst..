<script lang="ts">
	import { onMount } from 'svelte';
	import api, { ApiError } from '$lib/api';
	import Chart from '$lib/components/Chart.svelte';
	import type { Analysis, Dataset } from '$lib/types';

	let analyses: Analysis[] = $state([]);
	let datasets: Dataset[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let selectedDataset = $state('');

	async function load() {
		loading = true;
		error = '';
		try {
			const ds = await api.get<{ datasets: Dataset[] }>('/datasets');
			datasets = ds.datasets;
			const path = selectedDataset ? `/analyses?dataset_id=${selectedDataset}` : '/analyses';
			const res = await api.get<{ analyses: Analysis[] }>(path);
			analyses = res.analyses;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Could not load analysis history.';
		} finally {
			loading = false;
		}
	}

	function rowsOf(a: Analysis): Record<string, unknown>[] {
		const r = a.results?.result;
		if (Array.isArray(r)) return r as Record<string, unknown>[];
		if (r && typeof r === 'object' && 'points' in (r as object))
			return ((r as { points: Record<string, unknown>[] }).points ?? []) as Record<string, unknown>[];
		if (r && typeof r === 'object' && 'top' in (r as object))
			return ((r as { top: Record<string, unknown>[] }).top ?? []) as Record<string, unknown>[];
		return [];
	}

	onMount(load);
</script>

<svelte:head>
	<title>Analysis History — AI Data Analyst</title>
</svelte:head>

<div class="container page">
	<h1>Analysis History</h1>
	<p class="muted">Every question you have asked, with the answers computed from your datasets.</p>

	<div class="card filter-card">
		<select class="input" bind:value={selectedDataset} onchange={load}>
			<option value="">All datasets</option>
			{#each datasets as ds}
				<option value={ds.id}>{ds.original_filename}</option>
			{/each}
		</select>
		<button class="btn btn-secondary" onclick={load}>Refresh</button>
	</div>

	{#if loading}
		<p class="muted"><span class="spinner"></span> Loading history...</p>
	{:else if error}
		<div class="error-box">{error}</div>
	{:else if analyses.length === 0}
		<div class="card"><p class="muted">No analyses yet. Ask a question on a dataset to get started.</p></div>
	{:else}
		{#each analyses as a}
			<details class="card analysis">
				<summary>
					<div>
						<span class="badge badge-blue">{a.analysis_type}</span>
						<b class="q">{a.question}</b>
					</div>
					<span class="muted small">
						{new Date(a.created_at).toLocaleString()} · dataset #{a.dataset_id}
					</span>
				</summary>
				<div class="body">
					<p class="answer">{@html a.answer.replace(/\n/g, '<br/>')}</p>
					{#if rowsOf(a).length > 0}
						{@const rows = rowsOf(a)}
						{@const cols = rows[0] ? Object.keys(rows[0]) : []}
						<div class="result-table">
							<table class="data-table">
								<thead>
									<tr>{#each cols as c}<th>{c}</th>{/each}</tr>
								</thead>
								<tbody>
									{#each rows as row}
										<tr>
											{#each cols as c}
												<td>{typeof row[c] === 'object' ? JSON.stringify(row[c]) : String(row[c] ?? '—')}</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
					{#if a.chart_spec}
						<div class="chart-box"><Chart spec={a.chart_spec} /></div>
					{/if}
				</div>
			</details>
		{/each}
	{/if}
</div>

<style>
	.page {
		padding: 28px 20px 40px;
	}

	.page h1 {
		margin: 0 0 4px;
		font-size: 28px;
	}

	.filter-card {
		display: flex;
		gap: 10px;
		align-items: center;
		margin: 16px 0;
		padding: 14px;
	}

	.filter-card .input {
		max-width: 300px;
	}

	.analysis {
		margin-bottom: 12px;
		padding: 14px 18px;
	}

	.analysis summary {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		cursor: pointer;
		list-style: none;
		flex-wrap: wrap;
	}

	.analysis summary::-webkit-details-marker {
		display: none;
	}

	.q {
		margin-left: 8px;
	}

	.small {
		font-size: 12px;
	}

	.body {
		margin-top: 12px;
		border-top: 1px solid var(--border);
		padding-top: 12px;
	}

	.answer {
		white-space: pre-wrap;
	}

	.result-table {
		margin-top: 10px;
		overflow-x: auto;
		max-height: 260px;
		overflow-y: auto;
		border: 1px solid var(--border);
		border-radius: 8px;
	}

	.chart-box {
		margin-top: 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 10px;
	}
</style>