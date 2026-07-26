# Single-Page How-To Site Spec

Pass a JSON object to `publish_single_page_site(site_spec_json, site_slug)`.

The renderer owns the Universal Agents visual treatment. It loads the shared
runtime theme and static polygon mesh used by Docs and Web Chat, then renders
the structured content into frosted panels with the embedded follow-up chat.
Do not add styling fields, raw HTML, scripts, CSS, Markdown tables, or alternate
theme instructions to the JSON spec.

Recommended shape:

```json
{
  "title": "How To ...",
  "summary": "Short practical description of the guide.",
  "audience": "Homeowner with basic hand tools",
  "conversation_id": "conversation_id_optional_focused_thread",
  "session_key": "optional_current_gateway_session_key",
  "thread_id": "optional_original_channel_thread_or_topic_id",
  "mirror_to_origin": true,
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
  ],
  "sections": [
    {
      "title": "Troubleshooting Notes",
      "body": "Use this section for domain-specific guidance.",
      "items": ["Humming can indicate a failed start capacitor."]
    }
  ],
  "resources": [
    {
      "label": "Manufacturer manual",
      "url": "https://example.com/manual",
      "notes": "Use the exact model manual when available."
    }
  ]
}
```

The renderer escapes HTML. Use plain text values; do not include raw HTML,
scripts, CSS, color palettes, alternate layout instructions, or Markdown tables.

If `create_focused_conversation` was used first, copy its returned `conversation_id` into this spec. Keep the current gateway `session_key` when available so the website host can attach the new focused thread to the same user session. Include the original channel `thread_id` when available; the published URL uses that value first, then falls back to `conversation_id`, so operators can visually track which chat thread produced the page.

`mirror_to_origin` defaults to true in generated pages. The browser shows a checkbox that sends `mirror_to_origin` with chat requests; when checked and the site is attached to an original non-website channel session, the website host mirrors the web follow-up and assistant reply back to that original channel.
