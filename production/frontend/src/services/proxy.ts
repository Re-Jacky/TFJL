export const API_BASE_URL = 'http://localhost:8000';

interface Proxy {
  get: <T = any>(endpoint: string) => Promise<T>;
  post: <T = any>(endpoint: string, data?: any) => Promise<T>;
}

const proxy: Proxy = {
  get: async <T>(endpoint: string) => {
    const pid = window.localStorage.getItem('activeWindow');
    const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
      headers: {
        'x-pid': pid || ''
      }
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json() as T;
  },
  post: async <T>(endpoint: string, data?: any) => {
    const pid = window.localStorage.getItem('activeWindow');
    const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-pid': pid || ''
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json() as T;
  }
};

export default proxy;