<script lang="ts">
	let { columns, rows }: { columns: string[]; rows: Record<string, unknown>[] } = $props();

	function display(value: unknown): string {
		if (value === null || value === undefined) return '—';
		if (typeof value === 'object') return JSON.stringify(value);
		return String(value);
	}
</script>

<div class="table-scroll">
	<table class="data-table">
		<thead>
			<tr>
				{#each columns as col}
					<th>{col}</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each rows as row, i (i)}
				<tr>
					{#each columns as col}
						<td>{display(row[col])}</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.table-scroll {
		overflow-x: auto;
		max-height: 420px;
		overflow-y: auto;
		border: 1px solid var(--border);
		border-radius: 8px;
	}
</style>
