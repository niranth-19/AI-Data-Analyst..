<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/auth';

	const features = [
		{
			title: 'Upload CSV / Excel',
			description: 'Upload your dataset and get an instant preview with column types and row counts.'
		},
		{
			title: 'Data Quality Analysis',
			description: 'Automatic detection of missing values, duplicates, empty columns and outliers.'
		},
		{
			title: 'Ask in Natural Language',
			description: 'Ask "What is total sales?" or "Top products by revenue" and get answers computed from your actual data.'
		},
		{
			title: 'Statistics & Insights',
			description: 'Relevant summary statistics and AI-generated insights grounded in real calculations.'
		},
		{
			title: 'Visualizations',
			description: 'Bar, line, pie and scatter charts generated from your data.'
		},
		{
			title: 'PDF Reports',
			description: 'Generate a professional downloadable PDF report of the full analysis.'
		}
	];

	const workflow = [
		'Register / Login',
		'Upload data',
		'Review quality & statistics',
		'Clean data',
		'Ask questions',
		'Generate charts & insights',
		'Download PDF report'
	];

	function go(path: string) {
		goto(path);
	}
</script>

<svelte:head>
	<title>AI Data Analyst — Analyze your data with AI</title>
</svelte:head>

<section class="hero">
	<div class="container">
		<h1>Ask questions about your data. Get real answers.</h1>
		<p class="hero-sub">
			Upload a CSV or Excel file and let the AI Data Analyst compute statistics, detect quality
			issues, answer natural-language questions, and generate charts and PDF reports — all grounded
			in your actual dataset. No fabricated numbers.
		</p>
		<div class="hero-actions">
			<button class="btn btn-primary btn-lg" onclick={() => go($user ? '/dashboard' : '/register')}>
				{$user ? 'Go to Dashboard' : 'Get Started'}
			</button>
			{#if !$user}
				<button class="btn btn-secondary btn-lg" onclick={() => go('/login')}>Log in</button>
			{/if}
		</div>
	</div>
</section>

<section class="container">
	<h2 class="section-title">How it works</h2>
	<div class="workflow">
		{#each workflow as step, i}
			<div class="step">
				<span class="step-num">{i + 1}</span>
				<span>{step}</span>
			</div>
		{/each}
	</div>
</section>

<section class="container">
	<h2 class="section-title">Features</h2>
	<div class="grid-2">
		{#each features as f}
			<div class="card feature">
				<h3>{f.title}</h3>
				<p class="muted">{f.description}</p>
			</div>
		{/each}
	</div>
</section>

<section class="cta">
	<div class="container">
		<h2>Ready to analyze your data?</h2>
		<button class="btn btn-primary btn-lg" onclick={() => go($user ? '/dashboard' : '/register')}>
			Start now
		</button>
	</div>
</section>

<style>
	.hero {
		background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
		color: #fff;
		padding: 72px 0;
		text-align: center;
	}

	.hero h1 {
		color: #fff;
		font-size: 40px;
		max-width: 720px;
		margin: 0 auto 16px;
	}

	.hero-sub {
		font-size: 17px;
		max-width: 680px;
		margin: 0 auto 28px;
		opacity: 0.92;
	}

	.hero-actions {
		display: flex;
		justify-content: center;
		gap: 12px;
		flex-wrap: wrap;
	}

	.btn-lg {
		padding: 12px 26px;
		font-size: 16px;
	}

	.section-title {
		margin: 44px 0 20px;
		font-size: 26px;
	}

	.workflow {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
		margin-bottom: 8px;
	}

	.step {
		display: flex;
		align-items: center;
		gap: 8px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 999px;
		padding: 8px 16px 8px 8px;
		font-size: 14px;
	}

	.step-num {
		background: var(--primary);
		color: #fff;
		width: 26px;
		height: 26px;
		border-radius: 50%;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 13px;
		font-weight: 700;
	}

	.feature {
		min-height: 120px;
	}

	.feature h3 {
		margin: 0 0 6px;
		font-size: 18px;
	}

	.cta {
		margin-top: 48px;
		background: var(--primary-light);
		border-top: 1px solid var(--border);
		padding: 48px 0;
		text-align: center;
	}
</style>