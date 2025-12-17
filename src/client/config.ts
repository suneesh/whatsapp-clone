// API Configuration
const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// Use environment variables for production URLs
// In Vite, these are accessed via import.meta.env
const PROD_API_URL = import.meta.env.VITE_API_BASE_URL;
const PROD_WS_URL = import.meta.env.VITE_WS_URL;

// Validate that production URLs are configured
if (!isDevelopment && (!PROD_API_URL || !PROD_WS_URL)) {
  throw new Error('Production API URLs not configured. Set VITE_API_BASE_URL and VITE_WS_URL environment variables.');
}

export const API_BASE_URL = isDevelopment
  ? 'http://localhost:8787'
  : PROD_API_URL;

export const WS_URL = isDevelopment
  ? 'ws://localhost:8787/ws'
  : PROD_WS_URL;
