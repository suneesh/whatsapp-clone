// API Configuration
const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// Use environment variables for production URLs
// In Vite, these are accessed via import.meta.env
const PROD_API_URL = import.meta.env.VITE_API_BASE_URL;
const PROD_WS_URL = import.meta.env.VITE_WS_URL;

// Log to document if console not available (for debugging black screens)
const log = (msg: string) => {
  console.log('[CONFIG]', msg);
};

log(`isDevelopment: ${isDevelopment}`);
log(`PROD_API_URL: ${PROD_API_URL}`);
log(`PROD_WS_URL: ${PROD_WS_URL}`);

export const API_BASE_URL = isDevelopment
  ? 'http://localhost:8787'
  : PROD_API_URL || 'https://whatsapp-clone-worker.hi-suneesh.workers.dev';

export const WS_URL = isDevelopment
  ? 'ws://localhost:8787/ws'
  : PROD_WS_URL || 'wss://whatsapp-clone-worker.hi-suneesh.workers.dev/ws';

log(`Final API_BASE_URL: ${API_BASE_URL}`);
log(`Final WS_URL: ${WS_URL}`);
