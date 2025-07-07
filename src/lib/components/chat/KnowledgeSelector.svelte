<script lang="ts">
	import { knowledge, showSettings, settings, user, mobile, config } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Selector from './KnowledgeSelector/Selector.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	import { updateUserSettings } from '$lib/apis/users';
	const i18n = getContext('i18n');

	export let selectedKnowledgeBases = [''];
	export let disabled = false;

	export let showSetDefault = true;

	const saveDefaultKnowledgeBase = async () => {
		const hasEmptyKnowledgeBase = selectedKnowledgeBases.filter((it) => it === '');
		if (hasEmptyKnowledgeBase.length) {
			toast.error($i18n.t('Choose a knowledge base before saving...'));
			return;
		}
		settings.set({ ...$settings, knowledgeBases: selectedKnowledgeBases });
		await updateUserSettings(localStorage.token, { ui: $settings });

		toast.success($i18n.t('Default knowledge base updated'));
	};

	$: if (selectedKnowledgeBases.length > 0 && $knowledge && $knowledge.length > 0) {
		selectedKnowledgeBases = selectedKnowledgeBases.map((kb) =>
			$knowledge.map((k) => k.id).includes(kb) ? kb : ''
		);
	}
</script>

<div class="flex flex-col w-full items-start">
	{#each selectedKnowledgeBases as selectedKnowledgeBase, selectedKnowledgeBaseIdx}
		<div class="flex w-full max-w-fit">
			<div class="overflow-hidden w-full">
				<div class="mr-1 max-w-full">
					<Selector
						id={`${selectedKnowledgeBaseIdx}`}
						placeholder={$i18n.t('Select a knowledge base')}
						items={($knowledge || []).map((knowledgeBase) => ({
							value: knowledgeBase.id,
							label: knowledgeBase.name,
							knowledgeBase: knowledgeBase
						}))}
						triggerClassName="text-sm sm:text-base lg:text-lg"
						bind:value={selectedKnowledgeBase}
					/>
				</div>
			</div>

			{#if $user?.role === 'admin' || ($user?.permissions?.knowledge?.multiple ?? true)}
				{#if selectedKnowledgeBaseIdx === 0}
					<div
						class="  self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]"
					>
						<Tooltip content={$i18n.t('Add Knowledge Base')}>
							<button
								class=" "
								{disabled}
								on:click={() => {
									selectedKnowledgeBases = [...selectedKnowledgeBases, ''];
								}}
								aria-label="Add Knowledge Base"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="size-3.5"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
								</svg>
							</button>
						</Tooltip>
					</div>
				{:else}
					<div
						class="  self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]"
					>
						<Tooltip content={$i18n.t('Remove Knowledge Base')}>
							<button
								{disabled}
								on:click={() => {
									selectedKnowledgeBases.splice(selectedKnowledgeBaseIdx, 1);
									selectedKnowledgeBases = selectedKnowledgeBases;
								}}
								aria-label="Remove Knowledge Base"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="size-3"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
								</svg>
							</button>
						</Tooltip>
					</div>
				{/if}
			{/if}
		</div>
	{/each}
</div>

{#if showSetDefault}
	<div
		class="absolute text-left mt-[1px] ml-1 text-[0.7rem] text-gray-600 dark:text-gray-400 font-primary"
	>
		<button on:click={saveDefaultKnowledgeBase}> {$i18n.t('Set as default')}</button>
	</div>
{/if} 