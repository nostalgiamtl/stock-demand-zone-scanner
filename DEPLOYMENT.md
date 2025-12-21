# Streamlit Cloud Deployment Guide

Deploy your Stock Demand Zone Scanner to the cloud for free!

## Prerequisites

- GitHub account (create one at https://github.com if you don't have one)
- Streamlit Cloud account (sign up at https://share.streamlit.io using your GitHub account)

## Step-by-Step Deployment

### Step 1: Create a GitHub Repository

1. Go to https://github.com/new
2. Name your repository (e.g., `stock-demand-zone-scanner`)
3. Make it **Public** (required for free Streamlit Cloud hosting)
4. **Don't** initialize with README, .gitignore, or license (we already have these)
5. Click "Create repository"

### Step 2: Push Your Code to GitHub

Open a terminal in this directory and run these commands:

```bash
# Initialize git repository (if not already done)
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: Stock Demand Zone Scanner"

# Add your GitHub repository as remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Example:**
```bash
git remote add origin https://github.com/john-doe/stock-demand-zone-scanner.git
git branch -M main
git push -u origin main
```

### Step 3: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your repository: `YOUR_USERNAME/stock-demand-zone-scanner`
4. Set the following:
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** Choose a custom URL (e.g., `stock-scanner-yourname`)
5. Click "Deploy!"

### Step 4: Wait for Deployment

- First deployment takes 3-5 minutes
- You'll see a build log showing progress
- Once complete, your app will be live at your chosen URL!

## Deployment Settings

Your app is already configured with:
- ✅ Streamlit config in `.streamlit/config.toml`
- ✅ Dependencies in `requirements.txt`
- ✅ Python 3.9+ compatible code

## Common Issues & Solutions

### Issue: "ModuleNotFoundError"
**Solution:** Make sure `requirements.txt` is in the root directory and properly formatted.

### Issue: "App is taking too long to load"
**Solution:** This is normal for first-time scan. The app downloads data for 500+ stocks.

### Issue: "Failed to fetch S&P 500 tickers"
**Solution:** Streamlit Cloud might be blocking Wikipedia. Add a fallback ticker list in `utils.py`:

```python
def get_sp500_tickers():
    # Try Wikipedia first
    try:
        # ... existing code ...
    except:
        # Fallback to hardcoded list
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', ...]  # Add your tickers
```

### Issue: "App keeps restarting"
**Solution:** This happens when the app uses too much memory. Consider:
- Reducing lookback period default to 1 year
- Scanning fewer stocks at once
- Upgrading to Streamlit Cloud paid tier

## Updating Your App

After making changes locally:

```bash
git add .
git commit -m "Description of your changes"
git push
```

Streamlit Cloud will automatically redeploy within 1-2 minutes!

## App URL

Once deployed, your app will be available at:
```
https://YOUR_CUSTOM_URL.streamlit.app
```

Share this URL with anyone - no login required to use the app!

## Monitoring

- View app logs in Streamlit Cloud dashboard
- See usage metrics and errors
- Manage app settings and resources

## Cost

**FREE Plan includes:**
- 1 GB memory
- 1 CPU core
- Unlimited viewers
- Community support

**Paid Plans** (if you need more resources):
- More memory and CPU
- Private apps
- Priority support
- Starting at $20/month

## Security Notes

1. **Don't commit API keys** - Use Streamlit secrets for any API keys
2. **Public data only** - This app uses public Yahoo Finance data, so no concerns
3. **No user authentication** - Anyone with the URL can access the app

## Custom Domain (Optional)

Want to use your own domain? Streamlit Cloud paid plans support custom domains:
- `stocks.yourdomain.com` instead of `your-app.streamlit.app`

## Next Steps

1. ✅ Deploy to Streamlit Cloud
2. 📱 Share the URL on social media
3. ⭐ Star the repository on GitHub
4. 🔧 Customize the scanner for your needs
5. 💬 Gather feedback from users

## Support

- **Streamlit Docs:** https://docs.streamlit.io/streamlit-community-cloud
- **Community Forum:** https://discuss.streamlit.io
- **GitHub Issues:** Report bugs in your repository

Happy deploying! 🚀
