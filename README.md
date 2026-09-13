# 🎓 SVKM CED - Google Drive Academic & Exam Analytics Dashboard

An interactive, multi-page data analytics web application built with **Python**, **Streamlit**, and **Plotly**. The application securely connects to Google Drive, automatically detects assessment folders, and renders comprehensive, dedicated visual dashboards for each folder.

---

## 🌟 Key Features

- **Google Drive Integration**: Automatically discovers subfolders in your designated Drive directory and parses `.xlsx`, `.xls`, `.csv`, and native Google Sheets.
- **Dynamic Multi-Page Navigation**: Switch between assessment folders directly from the sidebar. Each folder gets an independent, dedicated dashboard.
- **Interactive Visualizations (Plotly)**:
  - 🏆 **KPI Metric Cards**: Total records, Average scores, Pass rate %, Highest & Lowest scores, Standard deviation.
  - 🍩 **Grade & Outcome Distribution**: Interactive donut charts.
  - 📊 **Distribution Histograms**: Score frequency histograms with mean benchmarks.
  - 📈 **Subject & Department Comparison**: Horizontal bar charts comparing group means.
  - 📦 **Score Spread (Box Plots)**: Interquartile ranges and outlier detection across divisions/sections.
  - 🎯 **Metric Correlation**: Scatter plots with trendline analysis (e.g. Attendance vs Marks).
  - 🧩 **Cross-Tabulation Matrix**: Heatmap matrices (e.g. Department vs Grade).
  - 📅 **Timeline Trends**: Evaluation tracking over time.
- **Dynamic Slicing & Filters**: Filter by subject, department, division, and numeric score ranges.
- **Data Explorer & Export**: Searchable data table with one-click CSV export.
- **Demo / Offline Mode**: Includes realistic mock data out of the box so you can explore the dashboard before configuring Google Drive credentials.

---

## 🔒 Security Notice

> **IMPORTANT**: Never hardcode or commit plain Google account passwords or private keys.
> Google Drive API authentication uses **Google Cloud Service Accounts**, ensuring zero risk of compromising your primary Google account.

---

## 🚀 Quickstart (Local Run)

### 1. Prerequisites
Ensure Python 3.10+ is installed.

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Launch the Application
```powershell
streamlit run app.py
```
The dashboard will open automatically in your default browser at `http://localhost:8501`.
*If no Google Drive credentials are configured, the app will automatically launch in **Demo Mode** with realistic sample data.*

---

## 🔗 Connecting Live Google Drive (3-Minute Setup)

### Step 1: Create a Google Cloud Service Account
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `SVKM-Exam-Dashboard`).
3. In the search bar, search for **Google Drive API** and click **Enable**.
4. Go to **APIs & Services > Credentials** > Click **Create Credentials** > **Service Account**.
5. Give it a name (e.g., `drive-reader`) and click **Done**.
6. Click on the created Service Account > Go to the **Keys** tab > **Add Key** > **Create new key** > Select **JSON**.
7. Download the JSON file and rename it to `service_account.json`. Place it in this project's root folder.

### Step 2: Share Your Google Drive Folder
1. Open your Google Drive in your browser.
2. Open the main parent folder containing your exam/assessment subfolders.
3. Click **Share** and paste your Service Account's email address (e.g., `drive-reader@svkm-exam-dashboard.iam.gserviceaccount.com`).
4. Set permissions to **Viewer**.
5. Copy the Folder ID from the URL bar:
   `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i` (The string after `/folders/` is your ID).

### Step 3: Configure Environment
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Open `.env` and set your folder ID:
```ini
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=your_actual_parent_folder_id
```
*(Alternatively, you can paste the Folder ID directly in the app's sidebar settings).*

---

## 🌐 Deploying on the Web via GitHub (Streamlit Community Cloud)

You can deploy this dashboard to the web completely free using **GitHub + Streamlit Community Cloud**:

### 1. Push Your Code to GitHub
Ensure `.gitignore` is present (this prevents your `service_account.json` or `.env` from ever being pushed to GitHub):
```powershell
git init
git add .
git commit -m "Deploy SVKM Exam Dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/exam-dashboard.git
git push -u origin main
```

### 2. Deploy on Streamlit Community Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
2. Click **New app**.
3. Select your repository: `YOUR_GITHUB_USERNAME/exam-dashboard`.
4. Branch: `main`, Main file path: `app.py`.
5. Click **Advanced settings...** > **Secrets**.
6. Paste your credentials in TOML format:
   ```toml
   GOOGLE_DRIVE_ROOT_FOLDER_ID = "your_google_drive_folder_id"

   [gdrive_service_account]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_KEY\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@project.iam.gserviceaccount.com"
   client_id = "..."
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "..."
   ```
7. Click **Deploy!**

Your web dashboard is now live on the internet! Any changes you push to GitHub will automatically rebuild and update your live app.

---

## 📂 Project Structure

```text
Exam Dashboard/
├── app.py                 # Core Streamlit multi-page web application
├── drive_service.py       # Google Drive API client & data parser (Excel/CSV/Sheets)
├── visualizer.py          # Plotly visualization & KPI statistics engine
├── mock_data.py           # Sample data generator for demo & offline testing
├── requirements.txt       # Python dependencies
├── .env.example           # Template for environment configuration
├── .gitignore             # Strict secret safeguards (.env, *.json, keys)
└── README.md              # Documentation & deployment guide
```
