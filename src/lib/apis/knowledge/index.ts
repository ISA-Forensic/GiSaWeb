import { WEBUI_API_BASE_URL } from '$lib/constants';

export const createNewKnowledge = async (
	token: string,
	name: string,
	description: string,
	accessControl: null | object
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name: name,
			description: description,
			access_control: accessControl
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getExternalKnowledgeBases = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge-bases`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			console.log('getExternalKnowledgeBases raw API response:', JSON.stringify(json, null, 2));
			let result = [];
			if (Array.isArray(json)) {
				result = json;
			} else if (Array.isArray(json?.data)) {
				result = json.data;
			} else if (Array.isArray(json?.data?.data)) {
				result = json.data.data;
			} else {
				result = [];
			}
			
			// Filter to only include external knowledge bases (exclude local ones)
			result = result.filter((kb: any) => 
				kb.knowledge_base_id && 
				kb.source !== 'local' && 
				kb.id !== kb.knowledge_base_id
			);
			
			console.log('getExternalKnowledgeBases filtered result:', JSON.stringify(result, null, 2));
			return result;
		})
		.catch((err) => {
			error = err?.detail ?? err?.message ?? err;
			console.error('getExternalKnowledgeBases error:', err);
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getKnowledgeBases = async (
	token: string = '',
	connections: object | null = null
) => {
	let error = null;
	
	// Use the external knowledge bases endpoint which should filter by permissions
	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge-bases`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			console.log('getKnowledgeBases raw API response:', JSON.stringify(json, null, 2));
			let result = [];
			if (Array.isArray(json)) {
				result = json;
			} else if (Array.isArray(json?.data)) {
				result = json.data;
			} else if (Array.isArray(json?.data?.data)) {
				result = json.data.data;
			} else {
				result = [];
			}
			console.log('getKnowledgeBases processed result:', JSON.stringify(result, null, 2));
			return result;
		})
		.catch((err) => {
			error = err?.detail ?? err?.message ?? err;
			console.error('getKnowledgeBases error:', err);
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getKnowledgeBaseList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/list`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getKnowledgeById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type KnowledgeUpdateForm = {
	name?: string;
	description?: string;
	data?: object;
	access_control?: null | object;
};

export const updateKnowledgeById = async (token: string, id: string, form: KnowledgeUpdateForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name: form?.name ? form.name : undefined,
			description: form?.description ? form.description : undefined,
			data: form?.data ? form.data : undefined,
			access_control: form.access_control
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const addFileToKnowledgeById = async (token: string, id: string, fileId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${id}/file/add`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			file_id: fileId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFileFromKnowledgeById = async (token: string, id: string, fileId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${id}/file/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			file_id: fileId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const removeFileFromKnowledgeById = async (token: string, id: string, fileId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${id}/file/remove`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			file_id: fileId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const resetKnowledgeById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${id}/reset`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteKnowledgeById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${id}/delete`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const reindexKnowledgeFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/reindex`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

//////////////////////////
// Knowledge Base Permissions Management
//////////////////////////

export interface KnowledgePermission {
	group_ids?: string[];
	user_ids?: string[];
}

export interface KnowledgePermissionsForm {
	read?: KnowledgePermission;
	write?: KnowledgePermission;
}

export interface KnowledgePermissionsResponse {
	id: string;
	name: string;
	description: string;
	user_id: string;
	access_control?: {
		read?: KnowledgePermission;
		write?: KnowledgePermission;
	};
	users_with_read_access: Array<{ id: string; name: string; email: string }>;
	users_with_write_access: Array<{ id: string; name: string; email: string }>;
	groups_with_read_access: Array<{ id: string; name: string }>;
	groups_with_write_access: Array<{ id: string; name: string }>;
}

export interface BulkPermissionsForm {
	knowledge_base_ids: string[];
	access_control: {
		read?: KnowledgePermission;
		write?: KnowledgePermission;
	};
}

export const getAllKnowledgePermissions = async (token: string): Promise<KnowledgePermissionsResponse[]> => {
	// Get knowledge bases from the external endpoint (same as chat page)
	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge-bases`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json();
		throw error?.detail ?? error?.message ?? 'Failed to fetch knowledge bases';
	}

	const data = await res.json();
	
	// Extract knowledge bases from response
	let knowledgeBases = [];
	if (Array.isArray(data)) {
		knowledgeBases = data;
	} else if (Array.isArray(data?.data)) {
		knowledgeBases = data.data;
	} else {
		knowledgeBases = [];
	}

	// Transform to permissions response format
	return knowledgeBases.map((kb: any) => ({
		id: kb.id,
		name: kb.name,
		description: kb.description || '',
		user_id: kb.user_id || '',
		access_control: kb.access_control,
		users_with_read_access: kb.users_with_read_access || [],
		users_with_write_access: kb.users_with_write_access || [],
		groups_with_read_access: kb.groups_with_read_access || [],
		groups_with_write_access: kb.groups_with_write_access || []
	}));
};

export const getKnowledgePermissions = async (token: string, id: string): Promise<KnowledgePermissionsResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${id}/permissions`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json();
		throw error?.detail ?? error?.message ?? 'Failed to fetch knowledge permissions';
	}

	return res.json();
};

export const updateKnowledgePermissions = async (
	token: string,
	id: string,
	permissions: KnowledgePermissionsForm
): Promise<KnowledgePermissionsResponse> => {
	// All knowledge bases use local permission management
	const endpoint = `${WEBUI_API_BASE_URL}/knowledge-bases/${id}/permissions`;

	// If permissions object is empty, set access_control to null for public access
	const access_control = Object.keys(permissions).length === 0 ? null : permissions;

	const res = await fetch(endpoint, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ access_control })
	});

	if (!res.ok) {
		const error = await res.json();
		throw error?.detail ?? error?.message ?? 'Failed to update knowledge permissions';
	}

	return res.json();
};

export const bulkUpdateKnowledgePermissions = async (
	token: string,
	bulkForm: BulkPermissionsForm
): Promise<{ success_count: number; total_requested: number; failed_updates: any[] }> => {
	// All knowledge bases use local permission management
	const endpoint = `${WEBUI_API_BASE_URL}/knowledge-bases/bulk-permissions`;

	const res = await fetch(endpoint, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(bulkForm)
	});

	if (!res.ok) {
		const error = await res.json();
		throw error?.detail ?? error?.message ?? 'Failed to bulk update knowledge permissions';
	}

	return res.json();
};
