import pandas as pd
import smtplib
import asyncio
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from browser_use import Agent, Browser, SystemPrompt
from browser_use.browser.browser import BrowserConfig
from langchain_ollama import ChatOllama
from pydantic import Field
from dotenv import load_dotenv
import os


class CustomSystemPrompt(SystemPrompt):
    def important_rules(self):
        existing = super().important_rules()
        return existing + "\n" + SYSTEM_PROMPT


def parse_email_from_result(raw_result: str) -> tuple[str, str]:
    """Extract subject and body from agent output. Returns (subject, body) or raises ValueError."""
    import re
    text = raw_result.strip()

    subject_idx = re.search(r"Subject:", text, re.IGNORECASE)
    if subject_idx:
        text = text[subject_idx.start() :]

    for marker in ["Research Summary:", "**Research Summary**", "\nRECRUITER DETAILS:"]:
        if marker in text:
            text = text.split(marker)[0].strip()

    # Find Subject line (case-insensitive, may have **bold**)
    subject_match = re.search(r"Subject:\s*(.+?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if not subject_match:
        raise ValueError("Could not find Subject line in output")
    subject = subject_match.group(1).strip()
    subject = re.sub(r"\*+", "", subject).strip()  # Remove markdown bold

    # Body starts after first blank line following Subject
    body_start = text.find("\n\n", subject_match.end())
    if body_start == -1:
        body_start = subject_match.end()
    body = text[body_start:].strip()
    body = re.sub(r"\*+", "", body).strip()  # Remove markdown bold

    # Post-process: replace [Your Name] with Vedant Bhalerao if LLM forgot
    body = re.sub(r"\[Your Name\]", "Vedant Bhalerao", body, flags=re.IGNORECASE)

    return subject, body


def send_email(sender_email, sender_password, receiver_email, subject=None, body=None):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject if subject else "Reaching out for Internship Opportunities"
    msg.attach(MIMEText(body if body else "This is the email body", "plain"))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Email sent successfully!")


def get_preprocessed_recruiter(recruiters):
    recruiters = recruiters.filter(regex='^(?!Unnamed)')
    recruiters = recruiters.filter(regex='^(?!Loom)')

    recruiters = recruiters.dropna(subset=['Email'])

    return recruiters


SYSTEM_PROMPT = """
    You are a browser automation agent that researches recruiters and their companies.
    STRICT RULES:
    - You may ONLY visit these two URLs: the recruiter's LinkedIn profile and the company's website.
    - Do NOT visit Google, Google News, Wikipedia, or any other website.
    - Do NOT scroll on LinkedIn pages. Extract only what is visible on initial load.
    - Do NOT click on any popups, ads, or cookie banners.
    - If a page is blocked (Cloudflare, CAPTCHA, login wall), skip it and note "Page blocked."
    - Limit yourself to a maximum of 5 total actions across both websites.
    - Do NOT invent or assume any information. Only use what you can see on the pages or what is provided in the prompt.

    RESEARCH TASKS:

    1. LINKEDIN (visit the recruiter's LinkedIn URL):
    - Current job title
    - Any visible specializations or interests
    - University or education background (if visible)

    2. COMPANY WEBSITE (visit the company URL):
    - What the company does (1-2 sentences)
    - Any open positions related to Cybersecurity (check careers page if easily accessible)

    FINAL OUTPUT:
    Output ONLY the email content. No preamble, no "Based on my research", no research summary, no explanations.
    Format your response exactly as:
    Subject: [your subject line]
    [blank line]
    [email body - the full message text]

    The email MUST:
    - Use ONLY the following details about me (do NOT change, embellish, or add to these):
        Name: Vedant Bhalerao
        Education: M.Engg. student at the University of Maryland, College Park
        Major: Cybersecurity
        Goal: Seeking internship opportunities in Cybersecurity
    - Sign off with "Vedant Bhalerao" — NEVER use "[Your Name]" or any placeholder; the signature must be exactly "Vedant Bhalerao"
    - Reference specific things found during research (recruiter's role, company details, open positions)
    - Do NOT claim shared alumni status, shared connections, or anything not explicitly confirmed
    - Do NOT fabricate quotes, statistics, or company news that were not seen on the pages
    - Keep it under 150 words
"""


pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

recruiters = pd.read_csv("Recruiter_Contacts.csv")
recruiters = get_preprocessed_recruiter(recruiters)

load_dotenv()
sender_email = os.getenv("sender_email")
sender_password = os.getenv("sender_password")


recruiter_objects = []
for i in range(len(recruiters)):
    recruiter = recruiters.iloc[i]
    json_object = {
        "Recruiter Name": recruiter["Full Name"],
        "Recruiter Email": recruiter["Email"],
        "Recruiter LinkedIn": recruiter["LinkedIn Link"],
        "Recruiter Headline": recruiter["Headline"],
        "Recruiter Seniority": recruiter["Seniority"],
        "Company Name": recruiter["Company Name"],
        "Company Website": recruiter["Company Website Full"],
        "Company Industry": recruiter["Industry"],
        "Company Short Description": recruiter["Company Short Description"]
    }
    recruiter_objects.append(json_object)




llm = ChatOllama(model="kimi-k2.5:cloud", temperature=0)

for recruiter_object in recruiter_objects:
    prompt = f"""
        RECRUITER DETAILS:
        - Name: {recruiter_object['Recruiter Name']}
        - Email: {recruiter_object['Recruiter Email']}
        - LinkedIn: {recruiter_object['Recruiter LinkedIn']}
        - Headline: {recruiter_object['Recruiter Headline']}
        - Seniority: {recruiter_object['Recruiter Seniority']}
        - Company: {recruiter_object['Company Name']}
        - Company Website: {recruiter_object['Company Website']}
        - Industry: {recruiter_object['Company Industry']}

        ALLOWED URLs (visit ONLY these two):
        1. {recruiter_object['Recruiter LinkedIn']}
        2. {recruiter_object['Company Website']}

        Research the recruiter's LinkedIn and the company website, then write the cold email as described in the system prompt
    """

    browser = Browser(config=BrowserConfig(headless=True))
    agent = Agent(
        llm=llm,
        task=prompt,
        browser=browser,
        system_prompt_class=CustomSystemPrompt,
        max_failures=10,
        max_actions_per_step=1,
        use_vision=False,
        save_conversation_path=None,
    )

    result = asyncio.run(agent.run())
    raw = result.final_result()

    if raw is None:
        print(f"Skipping {recruiter_object['Recruiter Name']} - agent failed to produce result")
        continue

    try:
        subject, body = parse_email_from_result(raw)
        # Output only the email content, ready for sending
        print("==========================================")
        print("Subject:", subject)
        print(body)
        print("==========================================")

        send_email(sender_email, sender_password, recruiter_object['Recruiter Email'], subject, body)


    except ValueError as e:
        print("Parse error:", e)
        print("Raw output:\n", raw)
        continue





# 1. LINKEDIN RESEARCH (visit the recruiter's LinkedIn profile):
# - Current job title and role description
# - How long they've been at the company
# - Any recent activity topics
# - Skills or specializations mentioned
# - Any shared connections, interests, or university affiliations

# 2. COMPANY RESEARCH (visit the company website):
# - What the company does (1-2 sentence summary)
# - Key products or services
# - Recent news, blog posts, or press releases
# - Open job positions related to Cybersecurity
# - Company tech stack if mentioned