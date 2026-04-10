# ⚡ TaskFlow — Agile Task Management Web App

A feature-rich, dark-themed task management app built with Flask & SQLite.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open in browser
http://localhost:5000
```

## 🔑 Demo Login
- **Email:** demo@taskflow.com
- **Password:** demo123

---

## ✨ Features

### Core
- ✅ Create, edit, delete tasks with rich metadata
- 📁 Project management with color + emoji customization
- 👤 User registration, login, profile with avatar picker
- 🔔 In-app notifications system

### Task Management
- 🗂 **Kanban Board** — drag-and-drop cards across columns
- 📋 **List View** — filterable, sortable task table
- 🏷 **Priority levels** — Low / Medium / High / Critical
- 🔖 **Tags** — freeform tagging for tasks
- ✔ **Subtasks** — checklists with live progress tracking
- 👁 **Status** — To Do → In Progress → Review → Done

### Agile / Scrum
- 🏃 **Sprint management** — create, activate, plan sprints
- ⚡ **Story points** — Fibonacci-scale estimates
- 📊 **Velocity tracking** — completed story points

### Time Tracking
- ⏱ **Built-in timer** — start/stop Pomodoro-style
- 📅 **Manual time logging** — log hours per task
- 📈 **Estimated vs Logged** visual comparison

### Analytics
- 📊 **Status distribution** — doughnut chart
- 📈 **Completion trend** — 7-day bar chart
- 🎯 **Priority breakdown** — horizontal bar chart
- 🏆 **Story points by project** — grouped bar chart
- ⏱ **Time tracking overview** — progress bar

### UX / Design
- 🌑 Dark theme with glassmorphism accents
- 🔍 Global real-time task search
- ⚠ Overdue & due-soon alerts dashboard
- 💬 Per-task comment threads
- 📝 Activity feed on every task
- 🎨 Custom project colors + emoji icons
- 📱 Responsive layout

---

## 🗂 Project Structure

```
taskflow/
├── app.py              # Main Flask app + routes
├── requirements.txt
├── templates/
│   ├── base.html       # Sidebar, topbar, shared CSS
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── tasks.html
│   ├── task_detail.html
│   ├── project.html
│   ├── projects.html
│   ├── analytics.html
│   ├── profile.html
│   └── _task_modal.html
└── instance/
    └── taskflow.db     # SQLite database (auto-created)
```

## 🛠 Tech Stack
- **Backend:** Flask, SQLAlchemy, SQLite
- **Frontend:** Vanilla HTML/CSS/JS, Chart.js
- **Fonts:** Syne (headings), DM Sans (body)
- **Icons:** Font Awesome 6
