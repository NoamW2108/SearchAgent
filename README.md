# 🔎 Simple Brand URL Finder

This is a lightweight **Python web app** that lets you type a brand or company name and returns its **official website URL** — verified to actually be online.

The search uses DuckDuckGo’s lightweight HTML search, filters out common platforms (Wikipedia, social media, etc.), verifies the domain, and returns the most likely official site.

---

## ✨ Features

- 🧠 Finds the **most likely official URL** of a brand or company.  
- ✅ Verifies the URL is alive before returning it.  
- 🚫 Filters out irrelevant sources like Wikipedia, LinkedIn, Amazon, etc.  
- ⚡ Simple and fast — works locally in your browser.  
- 🖼️ Clean, responsive UI with instant results.

---

## 🧰 Tech Stack

- **Python 3**
- [Flask](https://flask.palletsprojects.com/)
- [Requests](https://requests.readthedocs.io/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)

---

## 🪄 How to Run

1. **Clone this repo**:
   ```bash
   git clone https://github.com/NoamW2108/SearchAgent.git
   cd SearchAgent
   python app.py

- Open http://127.0.0.1:8000 in your browser.