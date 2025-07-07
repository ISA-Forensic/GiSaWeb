<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';

	import {
		getAllKnowledgePermissions,
		updateKnowledgePermissions,
		bulkUpdateKnowledgePermissions,
		type KnowledgePermissionsResponse
	} from '$lib/apis/knowledge';
	import { getAllUsers } from '$lib/apis/users';
	import { getGroups } from '$lib/apis/groups';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	import EditPermissionsModal from './EditPermissionsModal.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let knowledgeBases: KnowledgePermissionsResponse[] = [];
	let allUsers: any[] = [];
	let allGroups: any[] = [];
	let searchQuery = '';
	let selectedKnowledgeBases: string[] = [];
	let showBulkActions = false;
	let showEditModal = false;
	let selectedKnowledgeBase: KnowledgePermissionsResponse | null = null;

	// Bulk permissions (simplified to just access)
	let bulkUserIds: string[] = [];
	let bulkGroupIds: string[] = [];

	$: filteredKnowledgeBases = knowledgeBases.filter((kb) => {
		if (!searchQuery) return true;
		return (
			kb.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
			kb.description.toLowerCase().includes(searchQuery.toLowerCase())
		);
	});

	$: showBulkActions = selectedKnowledgeBases.length > 0;

	const loadData = async () => {
		try {
			loading = true;
			const [kbData, usersData, groupsData] = await Promise.all([
				getAllKnowledgePermissions(localStorage.token),
				getAllUsers(localStorage.token),
				getGroups(localStorage.token)
			]);

			knowledgeBases = kbData;
			allUsers = usersData.users || [];
			allGroups = groupsData || [];
		} catch (error) {
			console.error('Error loading permissions data:', error);
			toast.error($i18n.t('Failed to load permissions data'));
		} finally {
			loading = false;
		}
	};

	const handleSelectAll = (checked: boolean) => {
		if (checked) {
			selectedKnowledgeBases = filteredKnowledgeBases.map((kb) => kb.id);
		} else {
			selectedKnowledgeBases = [];
		}
	};

	const handleSelectKnowledgeBase = (kbId: string, checked: boolean) => {
		if (checked) {
			// Prevent duplicates
			if (!selectedKnowledgeBases.includes(kbId)) {
				selectedKnowledgeBases = [...selectedKnowledgeBases, kbId];
			}
		} else {
			selectedKnowledgeBases = selectedKnowledgeBases.filter((id) => id !== kbId);
		}
	};

	const applyBulkPermissions = async () => {
		try {
			const bulkForm = {
				knowledge_base_ids: selectedKnowledgeBases,
				access_control: {
					read: {
						user_ids: bulkUserIds,
						group_ids: bulkGroupIds
					},
					write: {
						user_ids: bulkUserIds,
						group_ids: bulkGroupIds
					}
				}
			};

			const result = await bulkUpdateKnowledgePermissions(localStorage.token, bulkForm);

			if (result.failed_updates.length > 0) {
				toast.warning(
					$i18n.t('Updated {{count}} knowledge bases with {{failures}} failures', {
						count: result.success_count,
						failures: result.failed_updates.length
					})
				);
			} else {
				toast.success(
					$i18n.t('Successfully updated permissions for {{count}} knowledge bases', {
						count: result.success_count
					})
				);
			}

			// Reset bulk selections
			selectedKnowledgeBases = [];
			bulkUserIds = [];
			bulkGroupIds = [];

			// Reload data
			await loadData();
		} catch (error) {
			console.error('Error applying bulk permissions:', error);
			toast.error($i18n.t('Failed to update permissions'));
		}
	};

	const openEditModal = (kb: KnowledgePermissionsResponse) => {
		selectedKnowledgeBase = kb;
		showEditModal = true;
	};

	const handlePermissionUpdate = async () => {
		await loadData();
		showEditModal = false;
		selectedKnowledgeBase = null;
	};

	const getUserDisplayName = (userId: string) => {
		if (!userId) return 'Unknown';
		const user = allUsers.find((u) => u.id === userId);
		return user ? `${user.name} (${user.email})` : userId;
	};

	const getGroupDisplayName = (groupId: string) => {
		const group = allGroups.find((g) => g.id === groupId);
		return group ? group.name : groupId;
	};

	onMount(() => {
		loadData();
	});
</script>

<EditPermissionsModal
	bind:show={showEditModal}
	bind:knowledgeBase={selectedKnowledgeBase}
	{allUsers}
	{allGroups}
	on:updated={handlePermissionUpdate}
/>

<div class="w-full max-h-full">
	<div class="px-2.5 flex flex-col sm:flex-row justify-between items-center">
		<div class="text-lg font-medium py-3">{$i18n.t('Knowledge Base Permissions')}</div>
		
		<div class="flex items-center space-x-2">
			<input
				class="w-full text-sm bg-transparent border dark:border-gray-600 outline-hidden rounded-lg py-2 px-4"
				placeholder={$i18n.t('Search knowledge bases...')}
				bind:value={searchQuery}
			/>
		</div>
	</div>

	{#if showBulkActions}
		<div class="px-2.5 py-3 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500">
			<div class="flex flex-col space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">
						{$i18n.t('Bulk Actions')} ({selectedKnowledgeBases.length} {$i18n.t('selected')})
					</span>
					<button
						class="text-gray-500 hover:text-gray-700"
						on:click={() => (selectedKnowledgeBases = [])}
					>
						<XMark className="w-4 h-4" />
					</button>
				</div>

				<div class="space-y-4">
					<!-- Simplified Access Permissions -->
					<div class="space-y-2">
						<label class="text-sm font-medium">{$i18n.t('Who can access these knowledge bases?')}</label>
						
						<div class="space-y-1">
							<label class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Users')}</label>
							<select
								multiple
								class="w-full text-sm bg-transparent border dark:border-gray-600 rounded-lg py-2 px-3 min-h-[80px]"
								bind:value={bulkUserIds}
							>
								{#each allUsers as user}
									<option value={user.id}>{user.name} ({user.email})</option>
								{/each}
							</select>
							<div class="text-xs text-gray-500">{$i18n.t('Hold Ctrl/Cmd to select multiple users')}</div>
						</div>

						<div class="space-y-1">
							<label class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Groups')}</label>
							<select
								multiple
								class="w-full text-sm bg-transparent border dark:border-gray-600 rounded-lg py-2 px-3 min-h-[60px]"
								bind:value={bulkGroupIds}
							>
								{#each allGroups as group}
									<option value={group.id}>{group.name}</option>
								{/each}
							</select>
							<div class="text-xs text-gray-500">{$i18n.t('Hold Ctrl/Cmd to select multiple groups')}</div>
						</div>
					</div>
				</div>

				<div class="flex justify-end">
					<button 
						class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center"
						on:click={applyBulkPermissions}
					>
						<Check className="w-4 h-4 mr-2" />
						{$i18n.t('Apply to Selected')}
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if loading}
		<div class="flex justify-center items-center min-h-[200px]">
			<Spinner />
		</div>
	{:else}
		<div class="px-2.5">
			<div class="overflow-x-auto">
				<table class="w-full text-sm text-left">
					<thead class="bg-gray-50 dark:bg-gray-900">
						<tr>
							<th class="px-3 py-3 text-xs font-medium uppercase tracking-wider">
								<input
									type="checkbox"
									checked={selectedKnowledgeBases.length === filteredKnowledgeBases.length &&
										filteredKnowledgeBases.length > 0}
									indeterminate={selectedKnowledgeBases.length > 0 &&
										selectedKnowledgeBases.length < filteredKnowledgeBases.length}
									on:change={(e) => handleSelectAll(e.target.checked)}
									class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
								/>
							</th>
							<th class="px-3 py-3 text-xs font-medium uppercase tracking-wider">
								{$i18n.t('Knowledge Base')}
							</th>
							<th class="px-3 py-3 text-xs font-medium uppercase tracking-wider">
								{$i18n.t('Owner')}
							</th>
							<th class="px-3 py-3 text-xs font-medium uppercase tracking-wider">
								{$i18n.t('Access')}
							</th>
							<th class="px-3 py-3 text-xs font-medium uppercase tracking-wider">
								{$i18n.t('Actions')}
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
						{#each filteredKnowledgeBases as kb}
							<tr 
								class="hover:bg-gray-50 dark:hover:bg-gray-800 {selectedKnowledgeBases.includes(kb.id) ? 'bg-blue-50 dark:bg-blue-900/10 border-l-4 border-blue-500' : ''}"
							>
								<td class="px-3 py-4">
									<input
										type="checkbox"
										checked={selectedKnowledgeBases.includes(kb.id)}
										on:change={(e) => handleSelectKnowledgeBase(kb.id, e.target.checked)}
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
									/>
								</td>
								<td class="px-3 py-4">
									<div>
										<div class="font-medium">{kb.name}</div>
										<div class="text-xs text-gray-500">{kb.description}</div>
									</div>
								</td>
								<td class="px-3 py-4">
									<Badge content={getUserDisplayName(kb.user_id)} />
								</td>
								<td class="px-3 py-4">
									<div class="flex flex-wrap gap-1">
										{#if !kb.access_control}
											<Badge type="info" content={$i18n.t('Public')} />
										{:else}
											<!-- Show all users who have access (combining read and write, deduplicated by ID) -->
											{@const allUserIds = [...new Set([
												...(kb.users_with_read_access || []).map(u => u.id),
												...(kb.users_with_write_access || []).map(u => u.id)
											])]}
											{@const allGroupIds = [...new Set([
												...(kb.groups_with_read_access || []).map(g => g.id),
												...(kb.groups_with_write_access || []).map(g => g.id)
											])]}
											
											{#each allUserIds as userId}
												{@const user = [...(kb.users_with_read_access || []), ...(kb.users_with_write_access || [])].find(u => u.id === userId)}
												{#if user}
													<Badge content={user.name} />
												{/if}
											{/each}
											
											{#each allGroupIds as groupId}
												{@const group = [...(kb.groups_with_read_access || []), ...(kb.groups_with_write_access || [])].find(g => g.id === groupId)}
												{#if group}
													<Badge type="secondary" content={group.name} />
												{/if}
											{/each}
											
											{#if allUserIds.length === 0 && allGroupIds.length === 0}
												<Badge type="warning" content={$i18n.t('Owner Only')} />
											{/if}
										{/if}
									</div>
								</td>
								<td class="px-3 py-4">
									<Tooltip content={$i18n.t('Edit Permissions')}>
										<button
											class="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
											on:click={() => openEditModal(kb)}
										>
											<Pencil className="w-4 h-4" />
										</button>
									</Tooltip>
								</td>
							</tr>
						{/each}

						{#if filteredKnowledgeBases.length === 0}
							<tr>
								<td colspan="5" class="px-3 py-8 text-center text-gray-500">
									{#if searchQuery}
										{$i18n.t('No knowledge bases found matching your search.')}
									{:else}
										{$i18n.t('No knowledge bases available.')}
									{/if}
								</td>
							</tr>
						{/if}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div> 