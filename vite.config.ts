import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { defineConfig } from 'vite';

// On GitHub Pages the site is served under /<repo>/, so the production build
// needs that base path; dev runs at root.
const REPO_BASE = '/AstroRegolith/';

export default defineConfig(({ command }) => ({
  base: command === 'build' ? REPO_BASE : '/',
  // Honour $PORT so a supervisor that assigns a free port is obeyed; Vite would
  // otherwise walk up from 5173 and land somewhere the caller is not watching.
  server: process.env.PORT ? { port: Number(process.env.PORT), strictPort: true } : undefined,
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, '.') } },
}));
