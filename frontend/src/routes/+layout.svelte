<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import Navbar from '$lib/components/Navbar.svelte';
	import { authReady, loadUserFromStorage } from '$lib/auth';

	let { children } = $props();

	loadUserFromStorage();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

{#if $authReady}
	<Navbar />
	<main>
		{@render children()}
	</main>
{/if}