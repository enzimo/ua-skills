---
name: single-page-howto-site
description: Use this skill when a user asks for complex procedural guidance that should become a hosted Universal Agents-styled single-page website with materials, tools, safety notes, ordered checklist steps, plans, and an embedded follow-up chat with the agent.
---

# Single-Page How-To Site

## Overview

Use this skill to turn a complex how-to conversation into a hosted local website that the user can open in a browser. The generated site should be practical: safety notes, materials to buy, tools, plans, ordered checklist steps, assumptions, references, and the embedded chat panel.

Generated how-to sites must feel like part of Universal Agents. They use the same frosted surfaces, dark readable text, Inter/system font stack, ocean-blue controls, and static polygonal mesh background as Web Chat and Docs. Do not invent a separate visual theme, dark dashboard, marketing landing page, or custom CSS/HTML shell for the guide.

## Workflow

1. Clarify the task before publishing.
   Ask only the questions needed to make the guide specific enough to act on. For repair, electrical, mechanical, legal, medical, or other high-risk domains, clarify the user's exact equipment/context, constraints, experience level, and safety boundaries.

2. Decide whether a website is warranted.
   Use the website format when the answer contains multi-step instructions, a shopping list, setup plans, or something the user will execute over time. For short answers, answer normally.

3. Build a structured site spec.
   Use `references/site-spec.md` when you need the exact JSON shape. If `ui/DESIGN.md` exists in the workspace, read it before publishing and follow it for visual intent. Include conservative safety notes and explicit assumptions. Keep steps ordered, testable, and scoped to what the user actually asked. Provide content only; the renderer owns the Universal Agents visual styling and shared background.

4. Choose the conversation thread.
   For a short, already-focused conversation, keep the current thread by leaving the current `conversation_id` and `session_key` in the site spec. For a long or mixed conversation, first call `create_focused_conversation` with the relevant source turn indexes and a concise summary, then set the returned `conversation_id` in the site spec while preserving the current `session_key`. This gives the website chat a fresh focused thread without rewriting the original conversation.

5. Publish the site.
   Call `publish_single_page_site(site_spec_json, site_slug)` with a JSON object, not prose. Include the current channel `thread_id` when it is available; otherwise include `conversation_id`. The published URL starts with a safe thread/conversation tracking token so the page can be visually matched to the chat thread. The tool returns `site_url`, `site_id`, and file paths under the configured generated-site artifact directory.

6. Reply with the URL and important limits.
   Tell the user where to open the site and call out any unresolved assumptions or safety constraints. Mention that checklist state is saved in their browser and that the page's chat panel continues the same guide conversation when the website host and gateway are running. If the page is attached to an original channel session, its mirror checkbox can copy the web follow-up and assistant reply back to that original chat.

## Required Content

Every published how-to site should include:

- `title` and `summary`
- `safety_notes`, even if the note is that the task should be done by a qualified professional
- `materials` with quantities or selection guidance when applicable
- `tools`
- `plans` for preparation, execution, and validation when the work is complex
- `steps` with verification checks where possible
- `assumptions` describing what the guide depends on
- `resources` when useful for manuals, standards, or manufacturer documentation

## Visual Contract

- Follow `ui/DESIGN.md` when it is available. It is the source of truth for the Universal Agents polygon mesh, frosted surfaces, typography, colors, controls, Docs, Web Chat, and generated-site visual language.
- Rely on `publish_single_page_site` for page chrome, layout, shared runtime CSS, static polygonal background, checklist controls, and embedded chat styling.
- Keep the site spec to structured plain text values. Do not include raw HTML, scripts, CSS, Markdown tables, color palettes, or alternate design instructions in `sections` or other fields.
- Write copy that works inside frosted UI panels: concise headings, short paragraphs, scannable bullets, and checklist-friendly step titles.
- Use safety, warnings, and verification fields for emphasis instead of styling language such as "make this red" or "put this in a callout."
- If the user asks for a custom brand/theme for a walkthrough, explain that generated Universal Agents walkthroughs intentionally preserve the product UI style for consistency and readability.

## Guardrails

Do not publish a site that makes an unsafe request look routine. If the safe answer is to stop and hire a licensed professional, make that the guide's main plan. Do not invent equipment-specific details; ask or state assumptions instead.

For current prices, regulations, model-specific manuals, product recommendations, or other changing facts, verify with current sources before generating the site.
