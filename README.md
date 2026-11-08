# Scholarship-Advisory Rule-Based-System

BSD3513 Introduction to Artificial Intelligence - Lab Report 3 (Chapter 3: Knowledge Representation System)

A Streamlit web app that uses a rule-based system (facts + IF-THEN rules + inference engine) to decide scholarship eligibility: AWARD_FULL, AWARD_PARTIAL, REVIEW or REJECT.

Features
Enter applicant facts (CGPA, family income, co-curricular score, community service hours, semester, disciplinary actions)
Editable rules in JSON (with validation and a reset button)
Priority-based conflict resolution
Condition-by-condition explanation of every rule

Run locally
pip install -r requirements.txt
streamlit run StudentID_Lab3.py

Files
StudentID_Lab3.py - the application
requirements.txt - dependencies
