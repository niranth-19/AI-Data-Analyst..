<script lang="ts">
	import { onMount } from 'svelte';
	import api, { ApiError } from '$lib/api';
	import type { Dataset, Report } from '$lib/types';

	let datasets: Dataset[] = $state([]);
	let reports: Report[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let generating = $state(false);
	let genError = $state('');
	let genSuccess = $state('');

	let selectedDatasetId = $state('');
	let reportName = $state('');

	async function load() {
		loading = true;
		error = '';
		try {
			const [ds, rep] = await Promise.all([
				api.get<{ datasets: Dataset[] }>('/datasets'),
				api.get<{ reports: Report[] }>('/reports')
			]);
			datasets = ds.datasets;
			reports = rep.reports;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Could not load reports.';
		} finally {
			loading = false;
		}
	}

	async function generate() {
		if (!selectedDatasetId || generating) return;
		generating = true;
		genError = '';
		genSuccess = '';
		try {
			await api.post('/reports', {
				dataset_id: Number(selectedDatasetId),
				report_name: reportName.trim() || undefined
			});
			genSuccess = 'Report generated successfully.';
			await load();
		} catch (e) {
			genError = e instanceof ApiError ? e.message : 'Report generation failed.';
		} finally {
			generating = false;
		}
	}

	function download(report: Report) {
		api.getDownload(`/reports/${report.id}/download`, `${report.report_name.replace(/[^\w\-]+/g, '_')}.pdf`);
	}

	onMount(load);
</script>

<svelte:head>
	<title>Reports — AI Data Analyst</title>
</svelte:head>

<div class="container page">
	<h1>PDF Reports</h1>
	<p class="muted">Generate professional PDF reports containing dataset summary, quality, statistics, insights, Q&A and charts.</p>

	<div class="grid-2">
		<div class="card">
			<h2>Generate a new report</h2>
			<div class="field">
				<label class="label" for="ds">Dataset</label>
				<select id="ds" class="input" bind:value={selectedDatasetId}>
					<option value="">Select a dataset...</option>
					{#each datasets as ds}
						<option value={ds.id}>{ds.original_filename} ({ds.row_count} rows)</option>
					{/each}
				</select>
			</div>
			<div class="field">
				<label class="label" for="name">Report name (optional)</label>
				<input id="name" class="input" type="text" bind:value={reportName} placeholder="e.g. Q3 Sales Analysis" />
			</div>
			{#if genError}
				<div class="error-box">{genError}</div>
			{/if}
			{#if genSuccess}
				<div class="success-box">{genSuccess}</div>
			{/if}
			<button class="btn btn-primary" onclick={generate} disabled={generating || !selectedDatasetId}>
				{#if generating}<span class="spinner"></span> Generating...{:else}Generate report{/if}
			</button>
		</div>

		<div class="card">
			<h2>Your reports</h2>
			{#if loading}
				<p class="muted"><span class="spinner"></span> Loading reports...</p>
			{:else if reports.length === 0}
				<p class="muted">No reports generated yet.</p>
			{:else}
				<ul class="report-list">
					{#each reports as r}
						<li>
							<div>
								<b>{r.report_name}</b>
								<p class="muted small">
									Dataset #{r.dataset_id} · {new Date(r.created_at).toLocaleString()}
								</p>
							</div>
							<button class="btn btn-secondary" onclick={() => download(r)}>Download</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</div>
</div>

<style>
	.page {
		padding: 28px 20px 40px;
	}

	.page h1 {
		margin: 0 0 4px;
		font-size: 28px;
	}

	.field {
		margin-bottom: 14px;
	}

	.report-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.report-list li {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		padding: 10px 0;
		border-bottom: 1px solid var(--border);
	}

	.small {
		font-size: 12px;
		margin: 2px 0 0;
	}
</style>