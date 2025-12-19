import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ErrorBoundary } from './ErrorBoundary';
import './styles.css';

console.log('main.tsx: Starting application initialization');

// Hide loading message when app starts
const hideLoading = () => {
  const loadingEl = document.getElementById('loading');
  if (loadingEl) {
    loadingEl.style.display = 'none';
  }
};

try {
  const root = document.getElementById('root');
  if (!root) {
    throw new Error('Root element not found');
  }
  
  console.log('main.tsx: Root element found, rendering app');
  
  const reactRoot = ReactDOM.createRoot(root);
  reactRoot.render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>
  );
  
  // Hide loading after React mounts
  hideLoading();
  console.log('main.tsx: Application rendered successfully');
} catch (error) {
  console.error('main.tsx: Fatal error during application startup:', error);
  const loadingEl = document.getElementById('loading');
  if (loadingEl) {
    loadingEl.innerHTML = `<div style="padding: 20px; color: white; font-family: monospace;">
      <h2>Error Loading Application</h2>
      <p>${error instanceof Error ? error.message : 'Unknown error'}</p>
      <pre style="text-align: left; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 5px; overflow: auto; max-width: 600px;">${error instanceof Error ? error.stack : String(error)}</pre>
    </div>`;
  }
}
