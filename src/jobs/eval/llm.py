# src/jobs/eval/llm.py
from __future__ import annotations
import json
from typing import Dict, List
from openai import OpenAI

from pathlib import Path
import time

# load candidate profile from file
PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "candidate_profile.json"
with PROFILE_PATH.open() as f:
    CANDIDATE_PROFILE = json.load(f)

# --- Hard-coded for now; move to Sheets later ---
SYSTEM_MSG = """You are a concise recruiting-assistant bot helping evaluate job fit.
Return ONLY valid JSON with keys: 
- fit_score (0-10 integer)
- fit_notes (<=320 chars; provide more detail than one sentence)
- company_summary (<=100 chars)
- job_summary (≈200-250 chars)
No extra text—JSON only.
"""

# Model: pick a cheap+fast one. Change anytime.
MODEL_NAME = "gpt-4o-mini"

def _build_user_prompt(job: Dict) -> str:
    return json.dumps({
        "candidate_profile": CANDIDATE_PROFILE,
        "job_under_evaluation": job,
        "output_spec": {
            "fit_score": "integer 0-10 (10 = strong potential fit)",
            "fit_notes": "string <=320 chars; 2–3 sentences explaining rationale",
            "company_summary": "string <=100 chars; brief company + rough size/round if known",
            "job_summary": "string ~200-250 chars; summarize responsibilities & scope (no titles repeated)",
        },
    }, ensure_ascii=False)

def evaluate_jobs_simple(jobs: List[Dict]) -> List[Dict]:
    """
    For each normalized job dict, ask the LLM for:
      { "id": <job_id>, "fit_score": int, "fit_notes": str, "company_summary": str, "job_summary": str }
    Always returns all keys; on failure, uses safe defaults.
    """
    client = OpenAI()
    out: List[Dict] = []

    for j in jobs:
        user_prompt = _build_user_prompt(j)
        data = {}  # ensure defined even if parsing fails
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=400,  # more room for both summaries
            )
            text = resp.choices[0].message.content.strip()
            # tolerate fenced JSON
            if text.startswith("```"):
                # remove ```json ... ```
                text = text.strip("`")
                if text[:4].lower() == "json":
                    text = text[4:].strip()
            data = json.loads(text)
        except Exception as e:
            # leave data = {} and fall through to defaults below
            pass

        # Extract with sane defaults + caps
        fit_score = int(data.get("fit_score", 0)) if isinstance(data.get("fit_score"), (int, str)) else 0
        fit_notes = str(data.get("fit_notes", "")).strip()[:350]
        company_summary = str(data.get("company_summary", "")).strip()[:100]
        job_summary = str(data.get("job_summary", "")).strip()[:260]

        out.append({
            "id": str(j.get("id", "")),
            "fit_score": fit_score,
            "fit_notes": fit_notes,
            "company_summary": company_summary,
            "job_summary": job_summary,
        })

        # small pause to reduce rate-limit flakiness
        time.sleep(0.25)

    return out