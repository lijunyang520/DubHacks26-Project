"""
app.py - the Lend A Hand web server.

Run it from the project root with the venv active:

    python Backend/app.py

then open http://127.0.0.1:5001
"""
from flask import Flask, redirect, render_template, request, url_for

from matcher import DAYS, availabilityText, find_matches

# templates/ and static/ live in the project root, one folder up from this file
app = Flask(__name__, template_folder="../templates", static_folder="../static")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/sign-in")
def sign_in():
    return render_template("signInPage.html")


@app.route("/match", methods=["POST"])
def match():
    zip_code = request.form.get("zip", "").strip()
    skills = request.form.get("skills", "").strip()
    try:
        distance = int(request.form.get("distance", "10"))
    except ValueError:
        distance = 10

    # Each checked day sends day=mon, plus start_mon / end_mon from its time dropdowns
    availability = {}
    for day in request.form.getlist("day"):
        start = request.form.get(f"start_{day}")
        end = request.form.get(f"end_{day}")
        if day in DAYS and start and end and start < end:
            availability[day] = (start, end)

    search = {"zip": zip_code, "distance": distance, "skills": skills,
              "availability": availabilityText(availability)}

    if not (zip_code.isdigit() and len(zip_code) == 5):
        result = {"matches": [], "error": "Please enter a 5-digit ZIP code."}
    elif not availability:
        result = {"matches": [], "error": "Pick at least one day, with an end time after the start time."}
    else:
        result = find_matches(zip_code, distance, availability, skills)

    return render_template("results.html", search=search, **result)


# Visiting /match directly (a GET) just goes back to the search form
@app.route("/match", methods=["GET"])
def match_get():
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(port=5001, debug=True)   # macOS AirPlay already uses port 5000
