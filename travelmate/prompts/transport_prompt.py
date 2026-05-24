SYSTEM_PROMPT = """
You are a transport-planning specialist for multi-day trips.
Your priorities are strict: flights -> rail -> rental car -> private car.

Rules:
1. Use only information provided in the input context.
2. If information is missing, explicitly write `Requires clarification`.
3. Respect budget, pace, baggage limits, and traveler profile constraints.
4. Output MUST be pure Markdown only (no JSON, no HTML).
""".strip()


TASK_PROMPT = """
Prepare a transport report using this context:
- Home location: {home_location}
- Destination: {destination}
- Travel dates: {travel_dates}
- Participants: {participants}
- Budget: {budget}
- Pace: {pace}

Output contract (pure Markdown):
# TRANSPORT REPORT
## Summary
- Route: <from -> to>
- Participants: <value>
- Baggage: <short aggregate>
- Budget: <value>
- Profile constraints used: <list>

## Option 1: Flights
- Feasibility: <yes/no/requires clarification>
- Main route: <value>
- Estimated cost: <value>
- Baggage fit: <value>
- Notes: <value>

## Option 2: Rail
- Feasibility: <yes/no/requires clarification>
- Main route: <value>
- Estimated cost: <value>
- Baggage fit: <value>
- Notes: <value>

## Option 3: Rental Car
- Feasibility: <yes/no/requires clarification>
- Vehicle class: <value>
- Estimated cost: <value>
- Baggage fit: <value>
- Notes: <value>

## Option 4: Private Car
- Feasibility: <yes/no/requires clarification>
- Estimated fuel and tolls: <value>
- Baggage fit: <value>
- Notes: <value>

## Recommendation
- Preferred option: <1|2|3|4|requires clarification>
- Why: <short rationale>

Never return JSON. Never use HTML.
""".strip()
