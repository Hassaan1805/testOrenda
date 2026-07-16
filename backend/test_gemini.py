from gemini import generate_reflection

journal = """
Today I finished my Orenda backend.
I learned FastAPI and SQLite.
I'm excited to connect the frontend next.
"""

print(generate_reflection(journal))