<script>
	import { onMount } from 'svelte';
	import { knowledge, config, settings } from '$lib/stores';

	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import Knowledge from '$lib/components/workspace/Knowledge.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				knowledge.set(await getKnowledgeBases(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				));
			})()
		]);
	});
</script>

{#if $knowledge !== null}
	<Knowledge />
{/if}
