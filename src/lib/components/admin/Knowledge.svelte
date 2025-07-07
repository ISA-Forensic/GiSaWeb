<script lang="ts">
	import { getContext, tick, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';

	import KnowledgePermissions from './Knowledge/KnowledgePermissions.svelte';

	const i18n = getContext('i18n');

	let selectedTab = 'permissions';
	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		loaded = true;

		const containerElement = document.getElementById('knowledge-tabs-container');

		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Admin Panel')} | {$i18n.t('Knowledge Base Management')}
	</title>
</svelte:head>

{#if loaded}
	<div class="w-full max-h-full flex flex-col">
		<div class="px-2.5 flex justify-between items-center">
			<div class=" text-2xl font-semibold px-1">{$i18n.t('Knowledge Base Management')}</div>
		</div>

		<hr class=" border-gray-50 dark:border-gray-850" />

		<div class="flex flex-col lg:flex-row w-full">
			<div
				id="knowledge-tabs-container"
				class="flex-shrink-0 overflow-x-auto bg-white/5 scrollbar-hidden lg:w-60"
			>
				<div class="min-w-60 w-full flex flex-row lg:flex-col px-0.5 h-full">
					<button
						class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 lg:flex-none text-right transition {selectedTab ===
						'permissions'
							? 'bg-gray-200 dark:bg-gray-700'
							: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
						on:click={() => {
							selectedTab = 'permissions';
						}}
					>
						<div class=" self-center mr-2">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-4"
							>
								<path
									fill-rule="evenodd"
									d="M8 1a3.5 3.5 0 0 0-3.5 3.5V6A1.5 1.5 0 0 0 3 7.5v3A1.5 1.5 0 0 0 4.5 12h7a1.5 1.5 0 0 0 1.5-1.5v-3A1.5 1.5 0 0 0 11.5 6V4.5A3.5 3.5 0 0 0 8 1Zm2 5V4.5a2 2 0 1 0-4 0V6h4Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
						<div class=" self-center">{$i18n.t('Permissions')}</div>
					</button>
				</div>
			</div>

			<div class="flex-1 mt-1 lg:mt-0 overflow-y-scroll">
				{#if selectedTab === 'permissions'}
					<KnowledgePermissions />
				{/if}
			</div>
		</div>
	</div>
{/if} 