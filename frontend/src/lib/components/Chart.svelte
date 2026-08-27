<script lang="ts">
	import Chart from 'chart.js/auto';
	import { onDestroy } from 'svelte';
	import type { ChartSpec } from '$lib/types';

	let { spec }: { spec: ChartSpec | null } = $props();

	let canvasEl: HTMLCanvasElement | undefined = $state();
	let chart: Chart | undefined = $state();

	function render() {
		if (chart) {
			chart.destroy();
			chart = undefined;
		}
		if (!spec || !canvasEl) return;

		const isScatter = spec.type === 'scatter';
		const isPie = spec.type === 'pie' || spec.type === 'doughnut';
		const palette = [
			'#2563eb',
			'#16a34a',
			'#d97706',
			'#dc2626',
			'#7c3aed',
			'#0891b2',
			'#db2777',
			'#65a30d',
			'#ea580c',
			'#4f46e5'
		];

		const datasets = spec.datasets.map((ds) => ({
			label: ds.label,
			data: ds.data,
			backgroundColor: isPie ? palette : '#2563eb',
			borderColor: isPie ? palette : '#2563eb',
			tension: 0.3,
			fill: spec.type === 'line' ? true : false,
			pointRadius: isScatter ? 4 : 2,
			borderWidth: 1.5
		}));

		chart = new Chart(
			canvasEl,
			{
				type: (isScatter ? 'scatter' : isPie ? spec.type : spec.type === 'histogram' ? 'bar' : spec.type) as never,
				data: {
					labels: spec.labels,
					datasets
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: { display: datasets.length > 1 },
						title: { display: true, text: spec.title, font: { size: 14, weight: 600 } }
					},
					scales: isPie
						? undefined
						: {
								x: { ticks: { maxRotation: 45, font: { size: 10 } } },
								y: { beginAtZero: true }
							}
				}
			} as any
		);
	}

	$effect(() => {
		spec;
		canvasEl;
		render();
	});

	onDestroy(() => {
		if (chart) chart.destroy();
	});
</script>

<div class="chart-wrap">
	{#if spec}
		<canvas bind:this={canvasEl}></canvas>
	{:else}
		<p class="muted placeholder">No chart available for this result.</p>
	{/if}
</div>

<style>
	.chart-wrap {
		height: 320px;
		position: relative;
	}

	.placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
	}
</style>
