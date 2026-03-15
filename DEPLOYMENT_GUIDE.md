# Deploying Trackify to the Web 🚀

Right now, your website is running locally on your computer. The links I provided are "tunnels" that forward traffic to your Mac. If you turn off your computer or close the terminal, the website goes down.

To host Trackify **permanently** so anyone can access it 24/7, you can deploy it for free using a modern hosting provider. Here is a step-by-step guide to hosting it on **Render** (the easiest free option for Python websites).

---

### Step 1: Create a GitHub Repository
Render connects directly to your code repository to deploy and build the website automatically.
1. Sign up for a free account at [GitHub](https://github.com) if you don't have one.
2. Create a new repository (you can name it `trackify-expense-tracker`).
3. Upload all the files from your `tk2` folder onto GitHub (you can drag and drop them on the website or use the terminal).
   - *Note: Don't upload the `venv` or `.git` folders if they exist.*

### Step 2: Sign up for Render
1. Go to [Render.com](https://render.com) and click **Get Started**.
2. Sign up using your GitHub account (this makes it easy to link your code).

### Step 3: Create a New Web Service
1. In your Render Dashboard, click the **New** button and select **Web Service**.
2. Select **Build and deploy from a Git repository**.
3. Connect your GitHub account and select your `trackify-expense-tracker` repository.

### Step 4: Configure the Deployment Details
Fill in the following details on the Render setup page:
- **Name**: `trackify-website` (or whatever you prefer)
- **Environment**: `Python 3`
- **Region**: Automatically selected (usually US or Frankfurt)
- **Branch**: `main` (or `master`)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app` (I have already updated your code to support this!)

### Step 5: Setup Environment Variables
Scroll down to the **Environment Variables** section and click "Add Environment Variable". You will need to add two keys:
1. **Key**: `SECRET_KEY`
   - **Value**: `any-secure-random-string-like-a-password`
2. **Key**: `DATABASE_URL` *(Optional)*
   - Right now wait, Render provides a free PostgreSQL database, but your website is currently using a local file-based SQLite database (`instance/expense_tracker.db`). SQLite will be erased every time Render restarts your server (due to its ephemeral file system). To keep data permanently, you will need to provision a Free PostgreSQL Database on Render first, and paste the "Internal Database URL" here as the `DATABASE_URL` value. The website handles the rest!

### Step 6: Deploy!
Scroll to the bottom and click **Create Web Service**. 
Render will now install your dependencies and launch your website. It usually takes 2-3 minutes. Once it's done, you'll see a green "Live" badge and a permanent URL at the top left (like `https://trackify-website.onrender.com`).

Share that URL with everyone, and Trackify is officially live 24/7!
