/**
 * API Configuration
 * 
 * This file centralizes the API URL configuration.
 * Priority:
 * 1. NEXT_PUBLIC_API_URL environment variable (defined in .env.local)
 * 2. Falls back to http://localhost:8000 if not set
 * 
 * To use cloud backend: set NEXT_PUBLIC_API_URL=http://104.238.134.110 in frontend/.env.local
 * To use local backend: remove or comment out NEXT_PUBLIC_API_URL in .env.local
 */

// Get API URL from environment variable or default to localhost
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API endpoints
export const API_ENDPOINTS = {
  health: `${API_URL}/health`,
  chat: `${API_URL}/api/chat`,
  chatStream: `${API_URL}/api/chat/stream`,
  tts: `${API_URL}/api/voice/tts`,
  ttsStream: `${API_URL}/api/voice/tts/stream`,
  stt: `${API_URL}/api/voice/stt`,
  sttStream: `${API_URL}/api/voice/stt/stream`,
} as const;

/**
 * Helper function to make API requests
 * Automatically uses the configured API_URL
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Helper function to create EventSource for SSE streaming
 */
export function createEventSource(endpoint: string): EventSource {
  const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;
  return new EventSource(url);
}

// Log the current API URL in development
if (process.env.NODE_ENV === 'development') {
  const source = process.env.NEXT_PUBLIC_API_URL ? '.env.local' : 'default (localhost)';
  console.log(`🔗 API URL: ${API_URL} (from ${source})`);
}
