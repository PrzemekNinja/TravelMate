# Requirements Document

## Introduction

The AI Cost & Cache Dashboard is a standalone internal web application built as a proof-of-concept and showcase tool for the TravelMate project. It provides two complementary capabilities: a Token Cost Comparison Dashboard that visualises how many tokens a TravelMate trip-planning request consumes and what it would cost across eight popular LLM models, and a Semantic Cache Showcase that demonstrates how a knowledge cache for travel-related data can eliminate redundant LLM calls and reduce costs. The application is designed to be visually impressive, shareable as a standalone demo, and runnable independently from the main TravelMate backend.

---

## Glossary

- **Dashboard**: The AI Cost & Cache Dashboard web application described in this document.
- **Token_Cost_Module**: The sub-application responsible for token counting and cross-model cost comparison.
- **Cache_Module**: The sub-application responsible for demonstrating semantic caching behaviour.
- **LLM_Model**: A large language model offered by a provider (Anthropic, OpenAI, Google, or Meta/other) with a published per-token pricing schedule.
- **Provider**: A company that exposes LLM APIs — Anthropic, OpenAI, Google, or Meta/other (Llama/Kimi).
- **Token**: The atomic unit of text processed by an LLM; input and output tokens are counted separately.
- **Pricing_Table**: A static, in-application data structure mapping each LLM_Model to its current input and output token prices in USD per million tokens.
- **Trip_Request**: A JSON object conforming to the TravelMate `ItineraryInput` schema (destination, days, budget, pace, interests, etc.).
- **Trip_Response**: The final Markdown itinerary text produced by TravelMate agents for a given Trip_Request.
- **Token_Usage**: A record containing `input_tokens`, `output_tokens`, and `total_tokens` for a single LLM call or a simulated call.
- **Cost_Estimate**: The USD cost derived by multiplying Token_Usage counts against the Pricing_Table for a given LLM_Model.
- **Semantic_Cache**: An in-memory store of travel knowledge entries (city facts, attractions, transport options) indexed by vector embeddings for similarity-based retrieval.
- **Cache_Entry**: A single record in the Semantic_Cache consisting of a natural-language query key, its vector embedding, and a cached text response.
- **Similarity_Threshold**: A configurable cosine-similarity score (default 0.85) above which a query is considered a cache hit.
- **Cache_Hit**: A lookup result where a stored Cache_Entry has similarity ≥ Similarity_Threshold to the incoming query.
- **Cache_Miss**: A lookup result where no stored Cache_Entry meets the Similarity_Threshold.
- **Savings_Estimate**: The USD cost that would have been incurred by a full LLM call, avoided because a Cache_Hit was returned instead.

---

## Requirements

### Requirement 1: Application Shell and Navigation

**User Story:** As a developer or stakeholder, I want a polished, standalone web application with clear navigation between the two main modules, so that I can explore each capability independently without confusion.

#### Acceptance Criteria

1. THE Dashboard SHALL serve a single-page web application accessible at `http://localhost:3000` (or a configurable port) without requiring authentication.
2. THE Dashboard SHALL display a top-level navigation bar containing links to the Token Cost Comparison module and the Semantic Cache Showcase module.
3. WHEN a user clicks a navigation link, THE Dashboard SHALL render the corresponding module view without a full page reload.
4. THE Dashboard SHALL apply a consistent modern visual theme (dark or light, with accent colours) across all views, using a component library or design system.
5. THE Dashboard SHALL be responsive and render correctly on viewport widths from 1024 px to 2560 px.
6. IF the Dashboard backend is unavailable, THEN THE Dashboard SHALL display a clear error state with a retry option rather than a blank screen.

---

### Requirement 2: Token Cost Comparison — Input

**User Story:** As a developer, I want to provide a TravelMate trip-planning request and response so that the Dashboard can analyse token usage for that specific scenario.

#### Acceptance Criteria

1. THE Token_Cost_Module SHALL provide a text input area pre-populated with a sample TravelMate Trip_Request in JSON format.
2. WHEN a user edits the Trip_Request JSON and submits it, THE Token_Cost_Module SHALL validate the JSON structure against the TravelMate `ItineraryInput` schema.
3. IF the submitted JSON is syntactically invalid, THEN THE Token_Cost_Module SHALL display an inline validation error identifying the malformed field and prevent analysis from running.
4. THE Token_Cost_Module SHALL provide a second text input area for the Trip_Response (itinerary Markdown text), also pre-populated with a sample response.
5. THE Token_Cost_Module SHALL provide a "Run Analysis" button that triggers token counting and cost calculation.
6. WHEN the user has not yet submitted any input, THE Token_Cost_Module SHALL display the pre-populated sample data so the dashboard is immediately usable without manual entry.

---

### Requirement 3: Token Counting

**User Story:** As a developer, I want accurate token counts for the provided request and response text, so that cost estimates are grounded in real usage data.

#### Acceptance Criteria

1. WHEN a user submits a Trip_Request and Trip_Response, THE Token_Cost_Module SHALL compute `input_tokens` by tokenising the Trip_Request JSON string.
2. WHEN a user submits a Trip_Request and Trip_Response, THE Token_Cost_Module SHALL compute `output_tokens` by tokenising the Trip_Response Markdown string.
3. THE Token_Cost_Module SHALL compute `total_tokens` as the sum of `input_tokens` and `output_tokens`.
4. THE Token_Cost_Module SHALL use a tokenisation method compatible with the GPT-4 family (tiktoken `cl100k_base` encoding) as the reference tokeniser for all models, with a clearly labelled disclaimer that counts are approximate for non-OpenAI models.
5. WHEN token counts are computed, THE Token_Cost_Module SHALL display `input_tokens`, `output_tokens`, and `total_tokens` as numeric values in a summary panel before the per-model breakdown.

---

### Requirement 4: Multi-Model Cost Comparison

**User Story:** As a developer, I want to see the estimated USD cost for the same token usage across all supported LLM models side by side, so that I can make informed model-selection decisions.

#### Acceptance Criteria

1. THE Token_Cost_Module SHALL compute a Cost_Estimate for each of the following eight LLM_Models: Claude 3.5 Sonnet, Claude Haiku, GPT-4.1, GPT-4o-mini, Gemini 2.5 Flash, Gemini 1.5 Pro, Llama 3, and Kimi.
2. THE Token_Cost_Module SHALL derive each Cost_Estimate using the formula: `(input_tokens / 1_000_000 × input_price_per_million) + (output_tokens / 1_000_000 × output_price_per_million)`.
3. THE Token_Cost_Module SHALL store the Pricing_Table as a static configuration file that can be updated without code changes.
4. THE Token_Cost_Module SHALL display Cost_Estimates formatted to six decimal places in USD (e.g., `$0.001234`).
5. THE Token_Cost_Module SHALL visually highlight the cheapest model and the most expensive model in the comparison view.
6. WHEN the Pricing_Table is updated, THE Token_Cost_Module SHALL reflect the new prices on the next analysis run without requiring a server restart.

---

### Requirement 5: Cost Comparison Visualisation

**User Story:** As a developer or stakeholder, I want a visually compelling comparison of costs across models, so that the cost differences are immediately obvious and easy to communicate.

#### Acceptance Criteria

1. THE Token_Cost_Module SHALL render a horizontal bar chart showing Cost_Estimate per LLM_Model, sorted from cheapest to most expensive.
2. THE Token_Cost_Module SHALL render a data table alongside the chart showing, for each LLM_Model: provider name, model name, input token price, output token price, input cost, output cost, and total cost.
3. WHEN a user hovers over a bar in the chart, THE Token_Cost_Module SHALL display a tooltip with the exact Cost_Estimate and Token_Usage breakdown for that model.
4. THE Token_Cost_Module SHALL group models by Provider using distinct colour coding in both the chart and the table.
5. THE Token_Cost_Module SHALL display a "cost savings vs. most expensive" percentage for each model relative to the most expensive model in the set.

---

### Requirement 6: Semantic Cache — Knowledge Store

**User Story:** As a developer, I want the Cache_Module to maintain a pre-seeded set of travel knowledge entries, so that the cache demonstration is immediately meaningful without manual data entry.

#### Acceptance Criteria

1. THE Cache_Module SHALL initialise a Semantic_Cache pre-seeded with at least 20 Cache_Entries covering diverse travel topics: city overviews, top attractions, local transport options, cuisine highlights, and seasonal travel tips for at least five different destinations.
2. THE Cache_Module SHALL compute and store a vector embedding for each Cache_Entry key at initialisation time using a local or API-based embedding model.
3. THE Cache_Module SHALL display the full list of Cache_Entries in a browsable panel showing the query key, a truncated preview of the cached response, and the entry's creation timestamp.
4. WHEN the application starts, THE Cache_Module SHALL load the pre-seeded Cache_Entries into memory within 5 seconds.
5. THE Cache_Module SHALL allow a user to add a new Cache_Entry by providing a query key and response text through a form in the UI.
6. WHEN a new Cache_Entry is added, THE Cache_Module SHALL compute its embedding and insert it into the Semantic_Cache without restarting the application.

---

### Requirement 7: Semantic Cache — Query and Hit/Miss Visualisation

**User Story:** As a developer, I want to submit a query to the cache and see whether it hits or misses, along with the similarity score, so that I can understand how semantic matching works.

#### Acceptance Criteria

1. THE Cache_Module SHALL provide a query input field where a user can type a natural-language travel question.
2. WHEN a user submits a query, THE Cache_Module SHALL compute the query's embedding and compare it against all Cache_Entry embeddings using cosine similarity.
3. WHEN a Cache_Hit occurs, THE Cache_Module SHALL display the matched Cache_Entry's response, the similarity score (0.00–1.00), and a green "HIT" badge.
4. WHEN a Cache_Miss occurs, THE Cache_Module SHALL display a red "MISS" badge, the closest non-matching entry and its similarity score, and a message indicating that a full LLM call would be required.
5. THE Cache_Module SHALL display a real-time hit/miss history log showing the last 20 queries with their outcomes, similarity scores, and timestamps.
6. THE Cache_Module SHALL display aggregate statistics: total queries, total hits, total misses, and overall hit rate as a percentage.
7. WHEN the Similarity_Threshold is adjusted via a UI slider, THE Cache_Module SHALL re-evaluate the current query result immediately using the new threshold value.

---

### Requirement 8: Semantic Cache — Cost Savings Demonstration

**User Story:** As a developer or stakeholder, I want to see the monetary cost savings achieved by cache hits versus full LLM calls, so that I can quantify the business value of caching.

#### Acceptance Criteria

1. THE Cache_Module SHALL associate each Cache_Hit with a Savings_Estimate calculated as the Cost_Estimate that would have been incurred for the cached response text using a configurable reference LLM_Model (default: GPT-4o-mini).
2. THE Cache_Module SHALL display a running total of cumulative Savings_Estimate across all Cache_Hits in the current session.
3. THE Cache_Module SHALL display a side-by-side comparison panel showing "With Cache" cost (zero for hits) versus "Without Cache" cost (full LLM Cost_Estimate) for each query in the hit/miss history.
4. THE Cache_Module SHALL render a cumulative savings chart that updates in real time as new queries are submitted, showing total savings over the session timeline.
5. WHEN the reference LLM_Model for savings calculation is changed via a dropdown, THE Cache_Module SHALL recalculate all Savings_Estimates in the current session history immediately.

---

### Requirement 9: Standalone Deployment and Configuration

**User Story:** As a developer, I want the Dashboard to run as a self-contained application with minimal setup, so that it can be shared and demonstrated without depending on the TravelMate backend being live.

#### Acceptance Criteria

1. THE Dashboard SHALL be located in a dedicated subdirectory (`ai-cost-cache-dashboard/`) within the TravelMate workspace root, separate from the main TravelMate application code.
2. THE Dashboard SHALL include a `README.md` with step-by-step instructions to install dependencies and start the application using a single command.
3. THE Dashboard SHALL read API keys and configuration values from a `.env` file in its own directory, independent of the TravelMate root `.env`.
4. THE Dashboard SHALL function in a "demo mode" where all LLM calls and embedding computations use pre-computed mock data, allowing the application to run without any API keys.
5. WHEN demo mode is active, THE Dashboard SHALL display a visible banner indicating that mock data is being used.
6. THE Dashboard SHALL include a `docker-compose.yml` or equivalent single-command startup script so that the entire application can be launched without manual dependency installation beyond Docker.

---

### Requirement 10: Data Freshness and Pricing Accuracy

**User Story:** As a developer, I want the pricing data to be clearly dated and easy to update, so that cost comparisons remain trustworthy over time.

#### Acceptance Criteria

1. THE Dashboard SHALL display the date on which the Pricing_Table was last updated, visible in the Token Cost Comparison view.
2. THE Pricing_Table SHALL be stored in a human-readable format (JSON or YAML) with a `last_updated` field and per-model entries containing `input_price_per_million_usd` and `output_price_per_million_usd`.
3. WHEN the Pricing_Table `last_updated` date is more than 30 days in the past, THE Dashboard SHALL display a warning banner prompting the user to verify current pricing.
4. THE Dashboard SHALL include pricing data for all eight required LLM_Models at initial release, sourced from each provider's official pricing page.
