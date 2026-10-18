from dotenv import load_dotenv
import anthropic
import json
import os
import sqlite3

#opens .env file 
load_dotenv()
#sets up AI to a class name of ClaudeAI
claudeAI = anthropic.Anthropic()

#Gather User Info and presence
maxDist = int(input("What is the max distance you would travel? "))
datesFree = input("What time are you usually free throughout the week? (format: Sunday 8am-10am, 3pm-5pm; Monday 1pm-4pm)")
skillSet = input("any skills?")



#Calls AI
claudePrompt = f"""A volunteer is described:
Skill-set:  {skillSet }
Availability: {datesFree}
Availble Shifts: {availableShifts}
Which shift fits best for the user
"""



response = claudeAI.messages.create(
    model="claude-haiku-5-5",
    max_tokens=200,
    messages=[]
)