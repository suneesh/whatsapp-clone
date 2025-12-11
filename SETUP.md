# Quick Setup Guide

Follow these steps to get your WhatsApp clone running:

## Step 1: Install Dependencies
```bash
npm install
```

## Step 2: Login to Cloudflare (First time only)
```bash
npx wrangler login
```

## Step 3: Create D1 Database
```bash
npm run db:create
```

This will output something like:
```
[[d1_databases]]
binding = "DB"
database_name = "whatsapp_clone_db"
database_id = "xxxx-xxxx-xxxx-xxxx-xxxx"
```

**Copy the `database_id` value!**

## Step 4: Update wrangler.toml

Open `wrangler.toml` and replace `your-database-id` with the actual database ID from Step 3:

```toml
[[d1_databases]]
binding = "DB"
database_name = "whatsapp_clone_db"
database_id = "paste-your-id-here"  # Replace this!
```

## Step 5: Initialize Database Schema

For local development:
```bash
npm run db:init
```

For production:
```bash
npm run db:init:remote
```

## Step 6: Run the Application

Start both the backend and frontend:
```bash
npm run dev
```

This will start:
- Backend: http://localhost:8787
- Frontend: http://localhost:3000

## Step 7: Test the App

1. Open http://localhost:3000 in your browser
2. Enter a username and click "Continue"
3. Open another browser window (or incognito) at http://localhost:3000
4. Login with a different username
5. Start chatting in real-time!

## Deploy to Production

```bash
npm run deploy
```

After deployment, Cloudflare will give you a URL like `https://whatsapp-clone-worker.your-subdomain.workers.dev`

Update your frontend to use this URL in production.

## Troubleshooting

### "wrangler not recognized"
Use `npx wrangler` instead or the npm scripts which already include `npx`.

### Database errors
Make sure you've:
1. Created the database with `npm run db:create`
2. Updated the database_id in `wrangler.toml`
3. Initialized the schema with `npm run db:init`

### WebSocket connection failed
- Make sure both dev servers are running
- Check that the proxy is configured correctly in `vite.config.ts`
- Try restarting the dev servers

### Port already in use
Change the ports in `vite.config.ts` if needed.
