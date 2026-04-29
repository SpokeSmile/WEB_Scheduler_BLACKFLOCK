function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(';').shift();
  }
  return '';
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || 'Request failed');
    error.payload = data;
    error.status = response.status;
    throw error;
  }
  return data;
}

export function bootstrap() {
  return request('/api/bootstrap/', { method: 'GET' });
}

export function createSlot(payload) {
  return request('/api/slots/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateSlot(id, payload) {
  return request(`/api/slots/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteSlot(id) {
  return request(`/api/slots/${id}/delete/`, {
    method: 'DELETE',
  });
}

export function updateProfile(payload) {
  return request('/api/profile/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function changePassword(payload) {
  return request('/api/profile/password/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function disconnectDiscord() {
  return request('/api/discord/disconnect/', { method: 'POST' });
}

export function logout() {
  return request('/api/logout/', { method: 'POST' });
}
