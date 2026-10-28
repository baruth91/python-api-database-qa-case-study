"""Create the manual teaching schema once; never reset an existing schema."""

from app.database import database_url, initialize_schema

if __name__ == "__main__":
    initialize_schema(database_url(), "qa_demo")
    print("Initialized qa_demo with synthetic data. Run: python -m app.server")
