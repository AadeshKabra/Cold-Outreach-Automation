## Cold Outreach Email Automation

This project automates personalized cold email generation to recruiters and startup founders using a browser automation agent (`browser_use`), an LLM (`langchain-ollama`), and CSV contact lists. It can optionally send emails via Gmail SMTP.

### 1. Prerequisites

- **OS**: Windows 10 or later
- **Python**: 3.12 (or 3.10+ recommended)
- **Browser**: Chromium/Chrome installed (used by Playwright / `browser_use`)
- A Gmail account (only if you want to actually send emails)

### 2. Clone or set up the project folder

If you already have the folder (e.g. `D:\Cold Email`), you can skip cloning and just open it in your editor/terminal.

Otherwise:

```bash
cd D:\
git clone <your-repo-url> "Cold Email"
cd "Cold Email"
```

Or manually create a folder `D:\Cold Email` and place the project files there (`main.py`, `recruiters.py`, `startup_founders.py`, CSVs, etc.).

### 3. Create and activate a virtual environment (Windows, PowerShell)

From inside the project directory:

```bash
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1
```

Your prompt should now show `(venv)` at the beginning.

### 4. Install Python dependencies

Install all required packages:

```bash
pip install --upgrade pip
pip install pandas python-dotenv browser-use langchain-ollama pydantic
```

Depending on how `browser_use` is installed, Playwright may also need browser binaries:

```bash
python -m playwright install
```

If you later add a `requirements.txt`, you can instead run:

```bash
pip install -r requirements.txt
```

### 5. Prepare CSV input files

Place the following CSVs in the project root (`D:\Cold Email`):

- `Recruiter_Contacts.csv` – used by `recruiters.py` and `main.py`
- `Startup_Founder_Contacts.csv` – used by `startup_founders.py`

Each CSV should at least contain the columns referenced in the scripts, for example:

- For recruiters:
  - `Full Name`, `Email`, `LinkedIn Link`, `Headline`, `Seniority`,
    `Company Name`, `Company Website Full`, `Industry`, `Company Short Description`
- For startup founders:
  - `Full Name`, `Email`, `LinkedIn Link`, `Title`, `Seniority`,
    `Company Website Full`, `Company LinkedIn Link`, `Company State`, `Company Founded Year`

### 6. Configure environment variables (.env)

Create a `.env` file in the project root (`D:\Cold Email\.env`) with:

```env
sender_email=your_gmail_address@gmail.com
sender_password=your_app_password_here
```

**Important (Gmail):**

- Enable 2‑Step Verification on your Google account.
- Create an **App Password** (Google Account → Security → App passwords).
- Use the 16‑character app password as `sender_password` (do **not** use your normal Gmail password).

If you only want to generate emails and **not** send them, you can still set dummy values here and keep the `send_email(...)` calls commented out.

### 7. Running the recruiter workflow

From the project directory with the virtual environment active:

```bash
python recruiters.py
```

What it does:

- Reads `Recruiter_Contacts.csv`.
- For each recruiter, uses `browser_use` to:
  - Visit the recruiter’s LinkedIn profile and company website (within the strict rules in `SYSTEM_PROMPT`).
  - Ask the LLM (via `langchain-ollama`) to generate a short personalized cold email for **Vedant Bhalerao**.
- Parses the LLM output so only **usable email content** remains (subject + body).
- Prints the email to the console.
- Optionally sends it via Gmail using `send_email(...)` (if that line is enabled).

If you see `SMTPAuthenticationError`, check your `.env` and app password configuration.

### 8. Running the startup founder workflow

```bash
python startup_founders.py
```

What it does:

- Reads `Startup_Founder_Contacts.csv`.
- For each founder, uses `browser_use` to:
  - Visit the founder’s LinkedIn + company site (again under strict rules from `SYSTEM_PROMPT`).
  - Generate a concise, highly personalized email focused on cybersecurity internship contributions.
- Parses out subject + body and prints them.
- Optionally sends via Gmail if the `send_email(...)` call is enabled.

### 9. Notes on performance and stability

- **Network-bound:** Most time is spent loading LinkedIn / company sites and waiting for the LLM, not Python itself.
- **Blocked pages:** Some domains (LinkedIn login walls, Cloudflare) may be blocked. The agent will then fall back to using only task-provided info.
- **Retries:** Scripts use `max_failures` in the `Agent` config to avoid hanging indefinitely; you can lower this if individual contacts take too long.

### 10. Debugging common issues

- **`SMTPAuthenticationError (535)`**  
  - Check that `sender_email` and `sender_password` are correct.
  - Confirm you are using a Gmail **app password**, not your normal password.

- **Browser / Playwright errors (`NoneType has no attribute send`, etc.)**  
  - Stop the script, close stray browser processes, and re-run in a fresh terminal.
  - If needed, reduce the number of contacts per run or lower `max_failures`.

- **LinkedIn / company pages blocked**  
  - This is expected sometimes due to login walls or Cloudflare. The agent will write emails from the static info you provide in the CSV/task instead.

### 11. Typical workflow summary

1. Create and activate the virtual environment.
2. Install dependencies.
3. Add / update your CSV contact lists.
4. Create `.env` with Gmail credentials (app password).
5. Run `recruiters.py` and/or `startup_founders.py`.
6. Inspect generated emails in the terminal; enable `send_email(...)` if you want automatic sending.

