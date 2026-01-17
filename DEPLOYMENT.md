# 🚀 Deployment Guide: Market Forensics

## Part 1: Deploy Frontend to Vercel (2 minutes)

### Step 1: Import Project
1. Go to: **https://vercel.com/new**
2. Look for "Import Git Repository"
3. Search for: `projectbetterclass/Market-Forensics`
4. Click **"Import"**

### Step 2: Configure Project
Vercel will show a configuration screen. Set:

- **Project Name**: `market-forensics` (or whatever you want)
- **Framework Preset**: Next.js (should auto-detect)
- **Root Directory**: `frontend` ⚠️ IMPORTANT
- **Build Command**: `npm run build` (default, leave as-is)
- **Output Directory**: `.next` (default, leave as-is)
- **Install Command**: `npm install` (default, leave as-is)

### Step 3: Deploy
1. Click **"Deploy"** button
2. Wait 2-3 minutes for build to complete
3. You'll get a URL like: `https://market-forensics-xxxx.vercel.app`

✅ **Frontend is now live!** (But won't work fully until backend is connected)

---

## Part 2: Deploy Backend to Render (3 minutes)

### Step 1: Create Account
1. Go to: **https://render.com**
2. Sign up (can use GitHub login for quick auth)

### Step 2: Create New Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub account if prompted
3. Select repository: `projectbetterclass/Market-Forensics`
4. Click **"Connect"**

### Step 3: Configure Service
Fill in these settings:

- **Name**: `market-forensics-api`
- **Region**: Choose closest to you
- **Branch**: `main`
- **Root Directory**: `backend` ⚠️ IMPORTANT
- **Runtime**: `Python 3`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

### Step 4: Environment Variables (Optional)
If you have an OpenAI API key for LLM rendering, add:
- **Key**: `OPENAI_API_KEY`
- **Value**: `your-key-here`

### Step 5: Deploy
1. Click **"Create Web Service"**
2. Wait 3-5 minutes for build
3. You'll get a URL like: `https://market-forensics-api.onrender.com`

✅ **Backend is now live!**

---

## Part 3: Connect Frontend to Backend (1 minute)

### Step 1: Add Environment Variable to Vercel
1. Go to your Vercel project: https://vercel.com/dashboard
2. Click your `market-forensics` project
3. Go to **Settings** → **Environment Variables**
4. Add new variable:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://market-forensics-api.onrender.com` (your Render URL)
   - **Environment**: Select all (Production, Preview, Development)
5. Click **"Save"**

### Step 2: Redeploy
1. Go to **Deployments** tab
2. Click **"..."** on latest deployment
3. Click **"Redeploy"**
4. Wait 1-2 minutes

✅ **Everything is now connected and working!**

---

## 🎉 Your App is Live!

**Frontend URL**: Check Vercel dashboard  
**Backend URL**: Check Render dashboard

### Test It:
1. Visit your frontend URL
2. You should see a green "Backend Connected" banner
3. Try searching for a ticker (e.g., AAPL)
4. Select a date range and analyze

---

## 🔄 How to Update After Deployment

Just push to GitHub:
```bash
cd "C:\Users\Gebruiker\Documents\StockApp"
git add .
git commit -m "Update: your changes"
git push
```

Both Vercel and Render will automatically redeploy!

---

## ⚠️ Troubleshooting

### Frontend shows "Backend Disconnected"
- Check that `NEXT_PUBLIC_API_URL` is set in Vercel
- Verify backend URL is correct (no trailing slash)
- Check Render backend logs for errors

### Backend build fails on Render
- Check that Root Directory is set to `backend`
- Verify requirements.txt exists
- Check Render build logs for specific error

### "Module not found" errors
- Make sure `pip install -r requirements.txt` is in Build Command
- Check that all dependencies are in requirements.txt

---

## 📊 Free Tier Limits

**Vercel (Frontend)**:
- 100 GB bandwidth/month
- Unlimited deployments
- ✅ More than enough for this app

**Render (Backend)**:
- Free tier: Spins down after 15 min inactivity
- First request after sleep takes ~30 seconds
- ✅ Fine for testing/personal use

**Upgrade if needed**:
- Render: $7/month for always-on
- Vercel: Free tier is usually sufficient

---

## 🎯 Quick Links

- **Vercel Dashboard**: https://vercel.com/dashboard
- **Render Dashboard**: https://dashboard.render.com
- **GitHub Repo**: https://github.com/projectbetterclass/Market-Forensics
- **Vercel Docs**: https://vercel.com/docs
- **Render Docs**: https://render.com/docs
