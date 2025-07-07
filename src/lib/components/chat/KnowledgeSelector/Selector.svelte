<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import Fuse from 'fuse.js';

	import { flyAndScale } from '$lib/utils/transitions';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	import { user, knowledge, mobile, settings, config } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { getExternalKnowledgeBases } from '$lib/apis/knowledge';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let id = '';
	export let value = '';
	export let placeholder = 'Select a knowledge base';
	export let searchEnabled = true;
	export let searchPlaceholder = $i18n.t('Search a knowledge base');

	export let items: {
		label: string;
		value: string;
		knowledgeBase: any;
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		[key: string]: any;
	}[] = [];

	export let className = 'w-[32rem]';
	export let triggerClassName = 'text-lg';

	let show = false;

	let selectedKnowledgeBase = '';
	$: selectedKnowledgeBase = items.find((item) => item.value === value) ?? '';

	let searchValue = '';
	let selectedKnowledgeBaseIdx = 0;

	const fuse = new Fuse(
		items.map((item) => {
			const _item = {
				...item,
				knowledgeBaseName: item.knowledgeBase?.name,
				desc: item.knowledgeBase?.description
			};
			return _item;
		}),
		{
			keys: ['value', 'knowledgeBaseName', 'desc'],
			threshold: 0.4
		}
	);

	$: filteredItems = searchValue
		? fuse.search(searchValue).map((e) => {
				return e.item;
			})
		: items;

	const resetView = () => {
		selectedKnowledgeBaseIdx = 0;
	};

	$: if (searchValue) {
		resetView();
	}
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={async () => {
		searchValue = '';
		window.setTimeout(() => document.getElementById('knowledge-search-input')?.focus(), 0);

		resetView();
	}}
	closeFocus={false}
>
	<DropdownMenu.Trigger
		class="relative w-full font-primary"
		aria-label={placeholder}
		id="knowledge-selector-{id}-button"
	>
		<button
			class="flex w-full text-left px-0.5 py-1 outline-hidden bg-transparent truncate {triggerClassName} justify-between font-medium placeholder-gray-400 focus:outline-hidden transition-colors hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg min-h-[2.5rem] sm:min-h-0"
			on:mouseenter={async () => {
				try {
					const kbResult = await getExternalKnowledgeBases(localStorage.token);
					knowledge.set(kbResult);
				} catch (error) {
					console.error('Error fetching external knowledge bases:', error);
				}
			}}
			type="button"
		>
			{#if selectedKnowledgeBase}
				{selectedKnowledgeBase.label}
			{:else}
				{placeholder}
			{/if}
			<ChevronDown className=" self-center ml-2 size-3" strokeWidth="2.5" />
		</button>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		class=" z-40 {$mobile
			? `w-full`
			: `${className}`} max-w-[calc(100vw-1rem)] justify-start rounded-xl  bg-white dark:bg-gray-850 dark:text-white shadow-lg  outline-hidden"
		transition={flyAndScale}
		side={$mobile ? 'bottom' : 'bottom-start'}
		sideOffset={3}
	>
		<slot>
			{#if searchEnabled}
				<div class="flex items-center gap-2.5 px-5 mt-3.5 mb-1.5">
					<Search className="size-4" strokeWidth="2.5" />

					<input
						id="knowledge-search-input"
						bind:value={searchValue}
						class="w-full text-sm bg-transparent outline-hidden"
						placeholder={searchPlaceholder}
						autocomplete="off"
						on:keydown={(e) => {
							if (e.code === 'Enter' && filteredItems.length > 0) {
								value = filteredItems[selectedKnowledgeBaseIdx].value;
								show = false;
								return;
							} else if (e.code === 'ArrowDown') {
								selectedKnowledgeBaseIdx = Math.min(
									selectedKnowledgeBaseIdx + 1,
									filteredItems.length - 1
								);
							} else if (e.code === 'ArrowUp') {
								selectedKnowledgeBaseIdx = Math.max(selectedKnowledgeBaseIdx - 1, 0);
							} else {
								selectedKnowledgeBaseIdx = 0;
							}

							const item = document.querySelector(`[data-arrow-selected="true"]`);
							item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
						}}
					/>
				</div>
			{/if}

			<div class="px-3 max-h-64 overflow-y-auto scrollbar-hidden group relative">
				{#each filteredItems as item, index}
					<button
						aria-label="knowledge-base-item"
						class="flex w-full text-left font-medium line-clamp-1 select-none items-center rounded-button py-2 pl-3 pr-1.5 text-sm text-gray-700 dark:text-gray-100 outline-hidden transition-all duration-75 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer data-highlighted:bg-muted {index ===
						selectedKnowledgeBaseIdx
							? 'bg-gray-100 dark:bg-gray-800 group-hover:bg-transparent'
							: ''}"
						data-arrow-selected={index === selectedKnowledgeBaseIdx}
						data-value={item.value}
						on:click={() => {
							value = item.value;
							selectedKnowledgeBaseIdx = index;

							show = false;
						}}
					>
						<div class="flex flex-col">
							<div class="flex items-center gap-2">
								<div class="flex flex-col text-left">
									<div class="font-medium text-gray-800 dark:text-gray-100 line-clamp-1">
										{item.label}
									</div>
									{#if item.knowledgeBase?.description}
										<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
											{item.knowledgeBase.description}
										</div>
									{/if}
								</div>
							</div>
						</div>

						<div class="ml-auto pl-2 pr-1 flex gap-1.5 items-center">
							{#if value === item.value}
								<div>
									<Check className="size-3" />
								</div>
							{/if}
						</div>
					</button>
				{:else}
					<div class="">
						<div class="block px-3 py-2 text-sm text-gray-700 dark:text-gray-100">
							{$i18n.t('No results found')}
						</div>
					</div>
				{/each}
			</div>

			<div class="hidden w-[42rem]" />
			<div class="hidden w-[32rem]" />
		</slot>
	</DropdownMenu.Content>
</DropdownMenu.Root> 