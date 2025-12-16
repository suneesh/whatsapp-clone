// API Configuration
const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

export const API_BASE_URL = isDevelopment 
  ? 'http://localhost:8787'
  : 'https://whatsapp-clone-worker.hi-suneesh.workers.dev';

export const WS_URL = isDevelopment
  ? 'ws://localhost:8787/ws'
  : 'wss://whatsapp-clone-worker.hi-suneesh.workers.dev/ws';
