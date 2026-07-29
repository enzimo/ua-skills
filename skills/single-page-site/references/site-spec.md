# Single-Page Site Spec

Pass a JSON object to
`publish_single_page_site(site_spec_json, site_slug, site_kind)`.

The renderer owns the Universal Agents visual treatment. It loads the shared
runtime theme and static polygon mesh used by Docs and Web Chat, then renders
the structured content into frosted panels with the embedded follow-up chat.
Do not add styling fields, raw HTML, scripts, CSS, Markdown tables, or alternate
theme instructions to the JSON spec.

All kinds may use these common fields:

```json
{
  "title": "Page title",
  "summary": "Short description.",
  "conversation_id": "conversation_id_optional_focused_thread",
  "session_key": "optional_current_gateway_session_key",
  "thread_id": "optional_original_channel_thread_or_topic_id",
  "mirror_to_origin": true,
  "sections": [
    {
      "title": "Supporting Section",
      "body": "Concise content.",
      "items": ["Optional supporting point."]
    }
  ],
  "resources": [
    {
      "label": "Source",
      "url": "https://example.com/reference",
      "notes": "Why this source matters."
    }
  ]
}
```

For an `article`, optionally add:

```json
{
  "highlights": [
    {"title": "Main Finding", "body": "Concise explanation."}
  ],
  "key_points": ["Decision-relevant point."],
  "callouts": [
    {"title": "Worth Noting", "body": "A caveat or important context."}
  ]
}
```

For a `comparison`, optionally add:

```json
{
  "options": [
    {
      "name": "Option A",
      "summary": "What it is.",
      "best_for": "Who benefits most.",
      "pros": ["Advantage"],
      "cons": ["Tradeoff"]
    }
  ],
  "comparison_rows": [
    {
      "criterion": "Price",
      "values": {"Option A": "$30,000", "Option B": "$34,000"},
      "notes": "Comparable trim levels."
    }
  ],
  "recommendation": {
    "title": "Best fit",
    "summary": "Recommendation tied to the user's criteria.",
    "reasons": ["Reason grounded in evidence."]
  }
}
```

For a `how_to`, optionally add only relevant preparation and execution fields:

```json
{
  "safety_notes": [
    "Disconnect power and verify zero voltage before touching wiring."
  ],
  "materials": [
    {
      "name": "Replacement bearing",
      "quantity": "1",
      "notes": "Match the motor model and shaft size.",
      "required": true
    }
  ],
  "tools": [
    {
      "name": "Multimeter",
      "notes": "Rated for the circuit being tested.",
      "required": true
    }
  ],
  "plans": [
    {
      "title": "Preparation",
      "description": "Gather parts, isolate the work area, and confirm the motor nameplate.",
      "items": ["Photograph wiring before disconnecting anything."]
    }
  ],
  "steps": [
    {
      "title": "Verify the motor is de-energized",
      "details": "Turn off the breaker, lock out the switch if possible, and test line-to-line and line-to-ground.",
      "warning": "Do not continue if voltage is present.",
      "verification": "Meter reads zero on all relevant pairs."
    }
  ],
  "assumptions": [
    "The motor is small enough to service on a bench."
  ]
}
```

For an `app`, optionally add:

```json
{
  "stats": [
    {"label": "Weekly goal", "value": "4 sessions", "detail": "Strength and mobility"}
  ],
  "progress_trackers": [
    {
      "id": "workouts",
      "label": "Completed workouts",
      "current": 1,
      "target": 4,
      "unit": "sessions",
      "step": 1,
      "description": "Update after each session."
    }
  ],
  "checklist_items": [
    {"name": "Warm up before training", "notes": "Five easy minutes."}
  ],
  "actions": [
    {"label": "Exercise library", "url": "https://example.com/exercises"}
  ]
}
```

Treat every field above as optional. Include only values grounded in the user's
content. Do not add fake statistics, filler cards, arbitrary checklists, or
progress controls without meaningful state to track.

The renderer escapes HTML. Use plain text values; do not include raw HTML,
scripts, CSS, color palettes, alternate layout instructions, or Markdown tables.

If `create_focused_conversation` was used first, copy its returned `conversation_id` into this spec. Keep the current gateway `session_key` when available so the website host can attach the new focused thread to the same user session. Include the original channel `thread_id` when available; the published URL uses that value first, then falls back to `conversation_id`, so operators can visually track which chat thread produced the page.

`mirror_to_origin` defaults to true in generated pages. The browser shows a
checkbox that sends `mirror_to_origin` with chat requests; when checked and the
site is attached to an original non-website channel session, the website host
mirrors the web follow-up and assistant reply back to that original channel.

How-to checkboxes and app progress/checklist values are stored in the browser
for that page. Do not describe that convenience state as a durable team record.
