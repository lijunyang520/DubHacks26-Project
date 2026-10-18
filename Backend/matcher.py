"""
matcher.py - finds volunteer shifts that fit a person.

find_matches() runs the whole pipeline:
    ZIP -> coordinates -> shifts within the distance -> shifts inside the person's
    free hours -> Claude ranks the best few and says why each one fits.
If Claude can't be reached, a simple skill-overlap ranking is used instead.
"""
from datetime import datetime
from functools import lru_cache
import json
import os
import sqlite3

import anthropic
from dotenv import load_dotenv
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

#-------SETUP-------
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "volunteer.db")
load_dotenv(os.path.join(HERE, "..", ".env"))

claudeAI = anthropic.Anthropic(timeout=30.0)
geolocator = Nominatim(user_agent="dubhacks-volunteerApp")

DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
DAY_NAMES = dict(zip(DAYS, ["Sunday", "Monday", "Tuesday", "Wednesday",
                            "Thursday", "Friday", "Saturday"]))
TOP_N = 5
MAX_FOR_CLAUDE = 30   # only the closest 30 fitting shifts are sent, to keep the prompt small

# --------FUNCTIONS---------

#returns latitude and longitude of the ZIP, or None if the lookup fails.
#lru_cache remembers answers, so the same ZIP isn't looked up twice.
@lru_cache(maxsize=256)
def zip_to_coords(zip_code):
    try:
        location = geolocator.geocode({"postalcode": zip_code, "country": "US"}, timeout=5)
        if location is None:
            return None
        return location.latitude, location.longitude
    except Exception as e:
        print("Lookup error:", repr(e))
        return None

#returns the upcoming jobs within max_miles, closest first
def jobProximinity(user_lat, user_lon, max_miles):
    # mode=ro opens the database read-only, so this can never change its data
    database = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    database.row_factory = sqlite3.Row
    currDate = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = database.execute(
        """
        SELECT j.*, o.org_name
        FROM jobs j
        JOIN organizations o ON j.org_id = o.org_id
        WHERE j.start_time >= ?
        """,
        (currDate,),
    ).fetchall()
    database.close()

    nearbyJobs = []
    for row in rows:
        distMiles = geodesic((user_lat, user_lon), (row["latitude"], row["longitude"])).miles
        if distMiles <= max_miles:
            job = dict(row)
            job["distAway"] = round(distMiles, 1)
            job["skills_needed"] = json.loads(job["skills_needed"] or "[]")
            start = datetime.strptime(job["start_time"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(job["end_time"], "%Y-%m-%d %H:%M")
            job["day"] = DAYS[(start.weekday() + 1) % 7]  # Python's weekday() starts on Monday
            job["when"] = f"{start:%a %b} {start.day}, {_clock(start)} - {_clock(end)}"
            job["_start"], job["_end"] = start, end
            nearbyJobs.append(job)
    nearbyJobs.sort(key=lambda j: j["distAway"])
    return nearbyJobs

def _clock(t):
    return f"{t.hour % 12 or 12}:{t:%M} {'AM' if t.hour < 12 else 'PM'}"

#keeps only jobs that start and end inside the person's free hours that weekday.
#availability looks like {"mon": ("09:00", "17:00"), "sat": ("10:00", "14:00")}
def fitsAvailability(jobs, availability):
    fitting = []
    for j in jobs:
        if j["day"] not in availability:
            continue
        free_from, free_to = availability[j["day"]]
        # "HH:MM" strings compare correctly as text, so no time parsing is needed
        if free_from <= f"{j['_start']:%H:%M}" and f"{j['_end']:%H:%M}" <= free_to \
                and j["_start"].date() == j["_end"].date():
            fitting.append(j)
    return fitting

#turns the availability dict into text like "Monday 9:00 AM-5:00 PM; Saturday ..."
def availabilityText(availability):
    parts = []
    for day in DAYS:
        if day in availability:
            start, end = (datetime.strptime(t, "%H:%M") for t in availability[day])
            parts.append(f"{DAY_NAMES[day]} {_clock(start)}-{_clock(end)}")
    return "; ".join(parts)

#returns the jobs as one block of text, one job per line
def shiftsInString(jobs):
    lines = []
    for j in jobs:
        lines.append(
            f"{j['job_id']}. {j['title']} at {j['org_name']} - {j['description']} "
            f"| {j['distAway']} miles away | {j['when']} "
            f"| skills: {', '.join(j['skills_needed'])}"
        )
    return "\n".join(lines)

#asks Claude to pick the best jobs. Returns [(job, reason), ...] or raises on any problem.
def rankWithClaude(jobs, skills, availability):
    claudePrompt = f"""A volunteer is described:
Skills and interests: {skills or "not given"}
Availability: {availabilityText(availability)}

Every shift below already fits their availability and distance:
{shiftsInString(jobs)}

Pick the {TOP_N} shifts that best match their skills and interests, best first.
In each reason, only credit the volunteer with skills or interests they listed above.
Reply with only a JSON array, no other text, like:
[{{"job_id": 12, "reason": "One short sentence, to the volunteer, on why it fits."}}]"""

    response = claudeAI.messages.create(
        model="claude-haiku-5-5",
        max_tokens=4000,   # this model thinks first, and thinking counts toward the limit
        messages=[{"role": "user", "content": claudePrompt}],
    )
    if response.stop_reason == "max_tokens":
        raise ValueError("Claude ran out of tokens before answering")
    text = "".join(b.text for b in response.content if b.type == "text")
    # Keep just the [...] part in case Claude wraps it in a code block
    picks = json.loads(text[text.index("["): text.rindex("]") + 1])

    byId = {j["job_id"]: j for j in jobs}
    ranked = []
    for pick in picks:
        job = byId.get(int(pick["job_id"]))   # ignore any ID that wasn't in the list
        if job and all(job is not r[0] for r in ranked):
            ranked.append((job, str(pick["reason"])))
    if not ranked:
        raise ValueError("Claude returned no usable shifts")
    return ranked[:TOP_N]

#backup ranking with no AI: most shared skill words first, then closest
def rankBySkills(jobs, skills):
    words = {w.strip().lower() for w in skills.replace(",", " ").split() if len(w.strip()) > 2}

    def overlap(job):
        return [s for s in job["skills_needed"] if words & set(s.lower().split())]

    ranked = sorted(jobs, key=lambda j: (-len(overlap(j)), j["distAway"]))[:TOP_N]
    results = []
    for j in ranked:
        shared = overlap(j)
        if shared:
            reason = f"Uses your {', '.join(shared)} skills and is {j['distAway']} miles away."
        else:
            reason = f"Fits your schedule and is {j['distAway']} miles away."
        results.append((j, reason))
    return results

#the whole pipeline. Returns a dict the results page can show directly.
def find_matches(zip_code, max_miles, availability, skills):
    result = {"matches": [], "error": None, "used_ai": False, "nearby": 0}

    coords = zip_to_coords(zip_code)
    if coords is None:
        result["error"] = f"We couldn't find ZIP code {zip_code}. Check it and try again."
        return result

    nearby = jobProximinity(coords[0], coords[1], max_miles)
    result["nearby"] = len(nearby)
    if not nearby:
        result["error"] = f"No upcoming shifts within {max_miles} miles. Try a bigger distance."
        return result

    fitting = fitsAvailability(nearby, availability)
    if not fitting:
        result["error"] = (f"{len(nearby)} shifts are nearby, but none fall inside the hours "
                           "you picked. Try adding days or widening your hours.")
        return result

    try:
        ranked = rankWithClaude(fitting[:MAX_FOR_CLAUDE], skills, availability)
        result["used_ai"] = True
    except Exception as e:
        print("Claude ranking failed, using backup ranking:", repr(e), flush=True)
        ranked = rankBySkills(fitting, skills)

    for job, reason in ranked:
        match = {k: v for k, v in job.items() if not k.startswith("_")}
        match["reason"] = reason
        result["matches"].append(match)
    return result
