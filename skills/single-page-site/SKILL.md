---
name: single-page-site
description: Builds Universal Agents-styled single-page articles, comparisons, how-tos, and interactive apps with optional structured UI and embedded follow-up chat.
---

# Single-Page Site

## Overview

To turn content that benefits from a browser layout into a hosted local
website, use this skill. Choose the site's information shape before composing
it: `article`, `comparison`, `how_to`, or `app`.

To preserve the Universal Agents visual language, rely on the shared renderer
for frosted surfaces, dark readable text, Inter/system fonts, ocean-blue
controls, responsive layouts, and the static polygonal mesh background. Do not
invent a separate theme, dark dashboard, marketing shell, or arbitrary
model-authored HTML/CSS/JavaScript.

## Workflow

1. Decide whether a website is warranted.
   Use a site when a durable visual artifact will be easier to scan, compare,
   operate, or revisit than a normal chat response. For short answers, answer
   normally.

2. Choose the site kind from the information shape.
   - Default to `article` for explanations, reports, reference pages,
     collections, and content whose sections can be read independently.
   - Use `comparison` for evaluating alternatives such as products, vehicles,
     services, destinations, or plans.
   - Use `how_to` only when the user explicitly asks for instructions, a
     walkthrough, or a checklist, or when multiple user-executed actions must
     occur in a meaningful order.
   - Use `app` when browser-local interaction, state, or progress is part of
     the value, such as workout trackers, habit boards, practice logs, or goal
     dashboards.
   Do not choose `how_to` merely because the content contains bullets,
   recommendations, a conclusion, or possible next steps. If the main sections
   can be consumed in any order, choose another kind.

3. Clarify only material gaps.
   Ask only questions that change the page's accuracy or utility. For repair,
   electrical, mechanical, legal, medical, financial, or other high-risk
   domains, clarify the user's exact context, constraints, experience, and
   safety boundaries before publishing actionable guidance.

4. Build a structured site spec.
   Use `references/site-spec.md` for supported fields. If `ui/DESIGN.md`
   exists, read it before publishing. Treat UI elements as optional building
   blocks, not required template slots. Include only elements grounded in the
   content and omit empty cards, fake metrics, redundant callouts, and
   decorative controls.

5. Choose the conversation thread.
   For a short, already-focused conversation, keep the current thread by leaving the current `conversation_id` and `session_key` in the site spec. For a long or mixed conversation, first call `create_focused_conversation` with the relevant source turn indexes and a concise summary, then set the returned `conversation_id` in the site spec while preserving the current `session_key`. This gives the website chat a fresh focused thread without rewriting the original conversation.

6. Publish the site.
   Call `publish_single_page_site(site_spec_json, site_slug, site_kind)` with a JSON object, not prose. Include the current channel `thread_id` when available; otherwise include `conversation_id`. Use the selected typed kind rather than encoding the kind only in prose. The tool returns `site_url`, `site_id`, `site_kind`, and artifact paths.

7. Reply with the exact URL and important limits.
   Return the exact `site_url`; do not invent or shorten it. Call out unresolved
   assumptions or safety constraints. Mention browser-local state only when the
   page includes checklists, counters, or progress controls. Explain that the
   embedded chat can continue the same conversation when the website host and
   gateway are running.

## Optional UI Elements

- For `article`, consider content sections, key-point lists, highlight cards,
  callouts, and references.
- For `comparison`, consider option cards, criteria tables, pros and cons,
  best-fit notes, recommendations, and sources.
- For `how_to`, consider prerequisites, materials, tools, safety notes, ordered
  steps, warnings, verification checks, and progress checkboxes.
- For `app`, consider stat cards, counters, progress trackers, task or habit
  checklists, action links, and supporting content sections.
- For every kind, include `title`, `summary`, `sections`, and `resources` only
  when they help. Do not force every available element into the page.

## Visual Contract

- Follow `ui/DESIGN.md` when it is available. It is the source of truth for the Universal Agents polygon mesh, frosted surfaces, typography, colors, controls, Docs, Web Chat, and generated-site visual language.
- Rely on `publish_single_page_site` for page chrome, kind-specific layout, shared runtime CSS, static polygonal background, optional state controls, and embedded chat styling.
- Keep the site spec to structured plain text values. Do not include raw HTML, scripts, CSS, Markdown tables, color palettes, or alternate design instructions in `sections` or other fields.
- Write copy that works inside frosted UI panels: concise headings, short paragraphs, scannable bullets, compact cards, and clear labels.
- Use safety, warnings, and verification fields for emphasis instead of styling language such as "make this red" or "put this in a callout."
- If the user asks for a custom brand/theme, explain that generated Universal Agents sites intentionally preserve the product UI style for consistency and readability.

## Guardrails

Do not publish a site that makes an unsafe request look routine. If the safe
answer is to stop and hire a licensed professional, make that constraint
prominent. Do not invent equipment-specific details, comparison facts, progress
metrics, or user state; ask, research, or state assumptions instead.

For current prices, regulations, model-specific manuals, product recommendations, or other changing facts, verify with current sources before generating the site.
