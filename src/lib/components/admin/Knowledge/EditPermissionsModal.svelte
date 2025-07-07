<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		updateKnowledgePermissions,
		type KnowledgePermissionsResponse,
		type KnowledgePermissionsForm
	} from '$lib/apis/knowledge';

	import Modal from '$lib/components/common/Modal.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let knowledgeBase: KnowledgePermissionsResponse | null = null;
	export let allUsers: any[] = [];
	export let allGroups: any[] = [];

	let loading = false;
	let isPublic = false;
	let userIds: string[] = [];
	let groupIds: string[] = [];
	let ownerId = '';

	// Get admin users only for owner selection
	$: adminUsers = allUsers.filter(user => user.role === 'admin');

	// Available users/groups that aren't already selected
	$: availableUsers = allUsers.filter(
		(user) => !userIds.includes(user.id)
	);
	$: availableGroups = allGroups.filter(
		(group) => !groupIds.includes(group.id)
	);

	$: if (knowledgeBase) {
		resetForm();
	}

	const resetForm = () => {
		if (!knowledgeBase) return;

		// Set owner
		ownerId = knowledgeBase.user_id || '';

		// For external knowledge bases without access_control, default to public
		const hasAccessControl = knowledgeBase.access_control && 
			(knowledgeBase.access_control.read || knowledgeBase.access_control.write);
		
		isPublic = !hasAccessControl;
		
		// Combine read and write permissions into a single access list
		const readUsers = knowledgeBase.access_control?.read?.user_ids || [];
		const writeUsers = knowledgeBase.access_control?.write?.user_ids || [];
		const readGroups = knowledgeBase.access_control?.read?.group_ids || [];
		const writeGroups = knowledgeBase.access_control?.write?.group_ids || [];
		
		userIds = [...new Set([...readUsers, ...writeUsers])];
		groupIds = [...new Set([...readGroups, ...writeGroups])];
	};

	const addUser = (userId: string) => {
		if (userId && !userIds.includes(userId)) {
			userIds = [...userIds, userId];
		}
	};

	const removeUser = (userId: string) => {
		userIds = userIds.filter((id) => id !== userId);
	};

	const addGroup = (groupId: string) => {
		if (groupId && !groupIds.includes(groupId)) {
			groupIds = [...groupIds, groupId];
		}
	};

	const removeGroup = (groupId: string) => {
		groupIds = groupIds.filter((id) => id !== groupId);
	};

	const getUserName = (userId: string) => {
		const user = allUsers.find((u) => u.id === userId);
		return user ? user.name : 'Unknown User';
	};

	const getGroupName = (groupId: string) => {
		const group = allGroups.find((g) => g.id === groupId);
		return group ? group.name : 'Unknown Group';
	};

	const handlePublicToggle = (checked: boolean) => {
		isPublic = checked;
		if (isPublic) {
			// Clear all permissions when making public
			userIds = [];
			groupIds = [];
		}
	};

	const handleSave = async () => {
		if (!knowledgeBase) return;

		try {
			loading = true;

					const permissions: KnowledgePermissionsForm = {};

		if (!isPublic) {
			// Set the same permissions for both read and write
			permissions.read = {
				user_ids: userIds,
				group_ids: groupIds
			};
			permissions.write = {
				user_ids: userIds,
				group_ids: groupIds
			};
		} else {
			// For public access, don't set any permissions (will result in access_control = null)
		}

			await updateKnowledgePermissions(localStorage.token, knowledgeBase.id, permissions);

			toast.success($i18n.t('Permissions updated successfully'));
			dispatch('updated');
		} catch (error) {
			console.error('Error updating permissions:', error);
			toast.error($i18n.t('Failed to update permissions'));
		} finally {
			loading = false;
		}
	};

	const handleCancel = () => {
		show = false;
		resetForm();
	};

	// Simple event handlers
	const onUserSelectChange = (event: Event) => {
		const select = event.target as HTMLSelectElement;
		if (select.value) {
			addUser(select.value);
			select.value = '';
		}
	};

	const onGroupSelectChange = (event: Event) => {
		const select = event.target as HTMLSelectElement;
		if (select.value) {
			addGroup(select.value);
			select.value = '';
		}
	};
</script>

<Modal bind:show size="lg" on:close={handleCancel}>
	<div class="p-6">
		<!-- Modal Header -->
		<div class="flex items-center justify-between mb-6">
			<div class="flex items-center gap-2">
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
				<h2 class="text-lg font-semibold">{$i18n.t('Edit Permissions')} - {knowledgeBase?.name || ''}</h2>
			</div>
			<button
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
				on:click={handleCancel}
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		</div>

		<!-- Modal Content -->
		<div class="space-y-6">
		{#if knowledgeBase}
			<!-- Knowledge Base Info -->
			<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
				<h3 class="font-medium mb-2">{knowledgeBase.name}</h3>
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-2">{knowledgeBase.description}</p>
				
				<!-- Owner Selection (Admin Only) -->
				<div class="space-y-2">
					<label class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Owner')}</label>
					<select
						class="w-full text-sm bg-transparent border dark:border-gray-600 rounded px-2 py-1"
						bind:value={ownerId}
					>
						{#each adminUsers as user}
							<option value={user.id}>{user.name} ({user.email})</option>
						{/each}
					</select>
				</div>
			</div>

			<!-- Public/Private Toggle -->
			<div class="space-y-3">
				<div class="flex items-center space-x-3">
					<input
						type="checkbox"
						bind:checked={isPublic}
						on:change={() => handlePublicToggle(isPublic)}
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
					/>
					<div>
						<label class="font-medium">{$i18n.t('Public Access')}</label>
						<p class="text-sm text-gray-600 dark:text-gray-400">
							{$i18n.t('Allow all users to access this knowledge base')}
						</p>
					</div>
				</div>
			</div>

			<!-- Always show the access controls -->
			<div class="space-y-6">
				<!-- Simplified Access Permissions -->
				<div class="space-y-4">
					<h4 class="font-medium text-lg">{$i18n.t('Who can access this knowledge base?')}</h4>
					
					{#if isPublic}
						<div class="text-sm text-gray-500 italic bg-gray-50 dark:bg-gray-800 p-3 rounded">
							{$i18n.t('Knowledge base is set to public access. Uncheck "Public Access" above to configure specific user/group permissions.')}
						</div>
					{:else}

						<!-- Users -->
						<div class="space-y-2">
							<div class="flex items-center justify-between">
								<label class="text-sm font-medium">{$i18n.t('Users')}</label>
								<select
									class="text-sm bg-transparent border dark:border-gray-600 rounded px-2 py-1"
									on:change={onUserSelectChange}
								>
									<option value="">{$i18n.t('Add user...')}</option>
									{#each allUsers as user}
										<option value={user.id} disabled={userIds.includes(user.id)}>
											{user.name} ({user.email}) {userIds.includes(user.id) ? '(already selected)' : ''}
										</option>
									{/each}
								</select>
							</div>
							<div class="flex flex-wrap gap-2">
								{#each userIds as userId}
									{@const user = allUsers.find(u => u.id === userId)}
									<div class="inline-flex items-center px-3 py-1 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 rounded-full text-sm border border-blue-200 dark:border-blue-700">
										{user ? user.name : `Unknown User (${userId})`}
										<button
											class="ml-2 hover:text-red-500 p-1"
											on:click={() => removeUser(userId)}
											type="button"
										>
											<GarbageBin className="w-3 h-3" />
										</button>
									</div>
								{/each}
								{#if userIds.length === 0}
									<div class="text-sm text-gray-500">{$i18n.t('No users selected')}</div>
								{/if}
							</div>
						</div>

						<!-- Groups -->
						<div class="space-y-2">
							<div class="flex items-center justify-between">
								<label class="text-sm font-medium">{$i18n.t('Groups')}</label>
								<select
									class="text-sm bg-transparent border dark:border-gray-600 rounded px-2 py-1"
									on:change={onGroupSelectChange}
								>
									<option value="">{$i18n.t('Add group...')}</option>
									{#each allGroups as group}
										<option value={group.id} disabled={groupIds.includes(group.id)}>
											{group.name} {groupIds.includes(group.id) ? '(already selected)' : ''}
										</option>
									{/each}
								</select>
							</div>
							
							<div class="flex flex-wrap gap-2">
								{#each groupIds as groupId}
									{@const group = allGroups.find(g => g.id === groupId)}
									<div class="inline-flex items-center px-3 py-1 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 rounded-full text-sm border border-blue-200 dark:border-blue-700">
										{group ? group.name : `Unknown Group (${groupId})`}
										<button
											class="ml-2 hover:text-red-500 p-1"
											on:click={() => removeGroup(groupId)}
											type="button"
										>
											<GarbageBin className="w-3 h-3" />
										</button>
									</div>
								{/each}
								{#if groupIds.length === 0}
									<div class="text-sm text-gray-500">{$i18n.t('No groups selected')}</div>
								{/if}
							</div>
						</div>
					{/if}
					</div>

					<div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
						<p class="text-sm text-blue-800 dark:text-blue-200">
							<strong>{$i18n.t('Note')}:</strong>
							{$i18n.t('The knowledge base owner always has full access. Selected users and groups can use this knowledge base.')}
						</p>
					</div>
				</div>
		{/if}
		
		<!-- Modal Footer -->
		<div class="flex justify-end space-x-3 mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
			<button 
				type="button"
				class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50" 
				on:click={handleCancel} 
				disabled={loading}
			>
				{$i18n.t('Cancel')}
			</button>
			<button 
				type="button"
				class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center" 
				on:click={handleSave} 
				disabled={loading}
			>
				{#if loading}
					<svg class="animate-spin -ml-1 mr-3 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				{/if}
				{$i18n.t('Save Changes')}
			</button>
		</div>
	</div>
</Modal> 