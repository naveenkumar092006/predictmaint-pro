# 🏭 PredictMaint Pro v2 — Industrial Predictive Maintenance System

Railway-ready | Flask + ML Backend | Dark Industrial UI

---

## 🚀 Run Locally (VS Code)

```bash
cd predictive_maintenance
pip install -r requirements.txt
python app.py
```
Open → http://127.0.0.1:5000

---

## 👤 Login Credentials

| Username   | Password      | Role       |
|------------|---------------|------------|
| admin      | Admin@123     | Admin      |
| engineer1  | Engineer@123  | Engineer   |
| operator1  | Operator@123  | Operator   |
| manager1   | Manager@123   | Manager    |

---

## 🌐 Deploy to Railway

1. Sign up at github.com — upload ALL files from this folder
2. Sign up at railway.app — connect GitHub repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python app.py`
5. Generate Domain → Your app is live!

---

## 📁 File Structure

```
├── app.py              ← Flask routes + PDF + API
├── models.py           ← ML engine (RF + IsoForest + RUL)
├── auth.py             ← Login + roles + SQLite
├── config.py           ← Settings (Railway-ready)
├── requirements.txt    ← Dependencies
├── Procfile            ← Railway process file
├── runtime.txt         ← Python 3.10
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html  ← Main dashboard
│   ├── search.html
│   ├── analytics.html
│   └── users.html
└── static/
    ├── css/main.css
    └── js/main.js
```

---

## ✅ All Features

- Random Forest failure prediction
- Isolation Forest anomaly detection
- RUL (Remaining Useful Life) prediction
- Root cause deduction
- Smart maintenance planner + cost estimation (INR)
- PDF report download (ReportLab)
- Role-based auth (Admin/Engineer/Operator/Manager)
- Live simulation mode (AJAX 2-second updates)
- Web Audio alarm for critical machines
- Explainable AI feature importance chart
- Analytics dashboard (failures, costs, downtime)
- Morning startup daily health report
- Email alerts (SMTP or console simulation)
- Model evaluation (Accuracy, Precision, Recall, F1, Confusion Matrix)
