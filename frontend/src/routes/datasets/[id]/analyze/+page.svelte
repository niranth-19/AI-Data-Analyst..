<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import api, { ApiError } from '$lib/api';
	import Chart from '$lib/components/Chart.svelte';
	import type { AskResponse, Dataset } from '$lib/types';

	const dataset_id = Number(page.params.id);

	let dataset: Dataset | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let question = $state('');
	let asking = $state(false);

	interface ChatMessage {
		role: 'user' | 'assistant';
		content: string;
		chart?: AskResponse['chart_spec'] | null;
		results?: AskResponse['results'] | null;
		type?: string;
	}

	let messages: ChatMessage[] = $state([]);

	const suggestions = [
		'What is the total?',
		'Show the top values',
		'What are the main trends?',
		'Are there missing values?',
		'Summarize this dataset',
		'Show distribution'
	];

	async function ask(text: string) {
		if (asking || !text.trim()) return;
		const q = text.trim();
		question = '';
		messages = [...messages, { role: 'user', content: q }];
		asking = true;
		try {
			const res = await api.post<AskResponse>(`/datasets/${dataset_id}/ask`, { question: q });
			messages = [
				...messages,
				{
					role: 'assistant',
					content: res.answer,
					chart: res.chart_spec,
					results: res.results,
					type: res.analysis_type
				}
			];
		} catch (e) {
			messages = [
				...messages,
				{
					role: 'assistant',
					content: `⚠️ ${e instanceof ApiError ? e.message : 'Could not get an answer.'}`
				}
			];
		} finally {
			asking = false;
		}
	}

	function renderResultRows(results: AskResponse['results']): Record<string, unknown>[] {
		if (!results || typeof results !== 'object') return [];
		const result = (results as Record<string, unknown>).result;
		if (Array.isArray(result)) return result as Record<string, unknown>[];
		if (result && typeof result === 'object' && 'points' in (result as object)) {
			return ((result as { points: Record<string, unknown>[] }).points ?? []) as Record<string, unknown>[];
		}
		if (result && typeof result === 'object' && 'bins' in (result as object)) {
			return ((result as { bins: Record<string, unknown>[] }).bins ?? []) as Record<string, unknown>[];
		}
		if (result && typeof result === 'object' && 'top' in (result as object)) {
			return ((result as { top: Record<string, unknown>[] }).top ?? []) as Record<string, unknown>[];
		}
		return [];
	}

	onMount(() => {
		api
			.get<Dataset>(`/datasets/${dataset_id}`)
			.then((d) => {
				dataset = d;
			})
			.catch((e) => {
				error = e instanceof ApiError ? e.message : 'Could not load dataset.';
			})
			.finally(() => (loading = false));
	});
</script>

<svelte:head>
	<title>Analyze — {dataset?.original_filename ?? 'Dataset'} — AI Data Analyst</title>
</svelte:head>

<div class="container page">
	{#if loading}
		<p class="muted"><span class="spinner"></span> Loading...</p>
	{:else if error}
		<div class="error-box">{error}</div>
	{:else}
		<div class="head">
			<a href={`/datasets/${dataset_id}`} class="back">← Dataset details</a>
			<h1>AI Data Analysis</h1>
			<p class="muted">
				Analyzing <b>{dataset?.original_filename}</b> · {dataset?.row_count} rows. Answers are computed
				from your data and explained by AI.
			</p>
		</div>

		<div class="suggestions">
			{#each suggestions as s}
				<button class="chip" onclick={() => ask(s)} disabled={asking}>{s}</button>
			{/each}
		</div>

		<div class="chat">
			{#if messages.length === 0}
				<div class="welcome card">
					<p>Ask anything about your dataset, for example:</p>
					<ul>
						<li>"What is the average value?"</li>
						<li>"Which category has the highest total?"</li>
						<li>"Show me the trend over time"</li>
						<li>"Are there missing values or duplicates?"</li>
						<li>"Generate insights"</li>
					</ul>
				</div>
			{/if}

			{#each messages as m, i (i)}
				<div class="msg {m.role}">
					<div class="bubble">
						{#if m.role === 'user'}
							<p class="q-text">{m.content}</p>
						{:else}
							<p class="a-text">{@html m.content.replace(/\n/g, '<br/>')}</p>
							{#if m.results && renderResultRows(m.results).length > 0}
								{@const rows = renderResultRows(m.results)}
								{@const cols = rows[0] ? Object.keys(rows[0]) : []}
								<div class="result-table">
									<table class="data-table">
										<thead>
											<tr>
												{#each cols as c}<th>{c}</th>{/each}
											</tr>
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
							{#if m.chart}
								<div class="chart-box">
									<Chart spec={m.chart} />
								</div>
							{/if}
							{#if m.type}
								<span class="badge badge-blue type-badge">{m.type}</span>
							{/if}
						{/if}
					</div>
				</div>
			{/each}

			{#if asking}
				<div class="msg assistant">
					<div class="bubble">
						<span class="spinner"></span> Analyzing your data...
					</div>
				</div>
			{/if}
		</div>

		<form class="input-bar" onsubmit={(e) => { e.preventDefault(); ask(question); }}>
			<input
				class="input"
				placeholder="Ask a question about your data..."
				bind:value={question}
				disabled={asking}
			/>
			<button class="btn btn-primary" type="submit" disabled={asking || !question.trim()}>
				Ask
			</button>
		</form>
	{/if}
</div>

<style>
	.page {
		padding: 24px 20px 40px;
		max-width: 860px;
	}

	.back {
		font-size: 13px;
	}

	.head h1 {
		margin: 4px 0;
		font-size: 26px;
	}

	.suggestions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin: 16px 0;
	}

	.chip {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 999px;
		padding: 6px 14px;
		font-size: 13px;
		cursor: pointer;
	}

	.chip:hover {
		border-color: var(--primary);
		color: var(--primary);
	}

	.chat {
		display: flex;
		flex-direction: column;
		gap: 12px;
		margin-bottom: 16px;
	}

	.welcome {
		text-align: center;
		color: var(--muted);
	}

	.welcome ul {
		display: inline-block;
		text-align: left;
		margin: 0 auto;
	}

	.msg {
		display: flex;
	}

	.msg.user {
		justify-content: flex-end;
	}

	.bubble {
		max-width: 82%;
		padding: 12px 16px;
		border-radius: 14px;
		font-size: 14px;
	}

	.msg.user .bubble {
		background: var(--primary);
		color: #fff;
		border-bottom-right-radius: 4px;
	}

	.msg.assistant .bubble {
		background: var(--surface);
		border: 1px solid var(--border);
		border-bottom-left-radius: 4px;
		box-shadow: var(--shadow);
	}

	.q-text {
		margin: 0;
		white-space: pre-wrap;
	}

	.a-text {
		margin: 0;
		white-space: pre-wrap;
	}

	.chart-box {
		margin-top: 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 10px;
		background: #fff;
	}

	.result-table {
		margin-top: 10px;
		overflow-x: auto;
		max-height: 260px;
		overflow-y: auto;
		border: 1px solid var(--border);
		border-radius: 8px;
	}

	.type-badge {
		margin-top: 10px;
	}

	.input-bar {
		display: flex;
		gap: 8px;
		position: sticky;
		bottom: 16px;
		background: var(--surface);
		padding: 12px;
		border: 1px solid var(--border);
		border-radius: 12px;
		box-shadow: var(--shadow);
	}

	.input-bar .input {
		flex: 1;
	}
</style>