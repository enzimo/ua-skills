---
name: user-onboarding-guide
description: Guides early Universal Agents conversations with a warm opt-in tour of the team, sign-ins, the Inbox, schedules, objectives, memory, files and the Web Chat screen, then a menu of deeper and administrator topics, with remembered progress.
---

# User Onboarding Guide

## Overview

Use this skill to orient a new or early user who asks what the assistant can do,
asks for a tour, asks for help getting started, sends a first-session style
greeting where a short orientation offer would help, or asks to resume the
guide.

Treat onboarding as relationship-building, not as a feature list. Deliver a
welcoming first response, invite the user into a short guided tour, then reveal
capabilities one step at a time after the user opts in. Avoid one long
capability dump. Use a few appropriate emoji to make the walkthrough feel warm
and scannable, without turning the response into decoration.

The tour has two parts:

1. A **core tour** of about a dozen short steps that everyone gets.
2. A **menu** of deeper topics offered at the end. Administrator topics appear
   in the menu only for administrators.

## Start The Guide

To handle a first bare greeting such as "hello", "hi", or "hey":

1. Introduce the assistant using the assistant name from workspace context or
   runtime context when available, and include one friendly greeting emoji.
2. Give one warm sentence about the assistant's purpose in the user's life.
3. Offer to show the user around with a short guided walkthrough.
4. Ask whether to start. Do not include docs links in this first greeting.

Example first-greeting response:

```text
Hi Ach 👋 I am Leon, and I am here to become a practical personal helper: someone who learns how you like to work, remembers useful context, and helps move everyday things forward.

Since you are just getting started, I can show you around and give you a quick feel for what I can do. Want the short tour?
```

To handle a first request such as "tell me what you can do" or "what can you
do":

1. Introduce the assistant the same way, with one friendly greeting emoji.
2. Give one warm sentence about the assistant's purpose in the user's life.
3. Offer a short guided walkthrough.
4. Ask for permission to continue unless the user explicitly says to start the
   tour.

Do not answer the first request with categories, headings, bullets, or a map of
capabilities. Make the first response feel like a welcome, not documentation.

To handle `/tour` or an explicit "give me the tour": start the first core step
in the same reply, without asking first.

## Fit The Tour To The Person

Before the first step, read two lines from the turn's context and keep them for
the whole tour:

1. **Chat app.** Read `Channel:` under "Gateway Delivery Context".
   - `website` means Web Chat. Name the real buttons, tabs and pages.
   - `telegram` or `discord`: describe the in-chat buttons and give the Web
     Chat link for pages such as Settings or Workspace.
   - `whatsapp`, `signal`, `photon` (iMessage) and anything else: say that
     approvals and pages open as links, and give the Web Chat link.
   - Skip steps marked **Web Chat only** outside Web Chat.
2. **Role.** Read the `Person you work for:` line.
   - "an owner" or "an administrator": the person is an administrator. Offer
     the administrator topics in the menu.
   - "a member", or no such line: never show administrator topics, and never
     suggest commands only administrators can run.
   - Use the role only to choose what to explain. It grants nothing.

Build Web Chat links from the internal website base URL in workspace context.
If it is absent and `get_runtime_configuration_context` is available, call it
and read `environment.INTERNAL_WEBSITE_BASE_URL`. Web Chat is `/webchat`. If no
base URL is available, name the route instead of inventing a URL.

## Pace Messages

Send one step per top-level user turn, then stop and wait for the user's next
message. Do not chain steps, proactive notifications, or "next up" content in
the same turn.

- Keep each step to one short paragraph, or a sentence plus a short list, with
  at most one concrete example.
- Start with a short heading and one relevant emoji, such as
  `🧭 A Small Team Behind Me`.
- Highlight actions and copyable phrases with Markdown strong emphasis, such as
  `**Remind me every Friday to review open bills.**` Do not use raw HTML
  underline tags, because Web Chat renders them as literal text.
- Put commands in backticks, such as `/link cli:github`.
- End each step with a light prompt to continue, such as "Say **next** when
  you're ready."

After the second or third step, add once:

```text
You can say "finish" at any time to stop the guide. I will remember where we stopped and pick up from there next time you ask.
```

After that notice, send at most three more steps before asking whether to
continue, open the docs, or try an example.

## Core Tour

Cover these steps in order. Read
[core-steps.md](references/core-steps.md) for each step's facts, wording and
chat-app variants before sending it.

| Step id | Topic |
|---|---|
| `team` | The team lead and the specialists behind it |
| `screen_map` | **Web Chat only.** Where things are on the screen |
| `tools` | Doing real work with tools, and automatic setup |
| `sign_in` | Signing in to services without pasting secrets |
| `inbox` | Agents ask before they act: the Inbox |
| `schedules` | Reminders and recurring checks |
| `objectives` | Bigger goals the team keeps working on |
| `pages` | Checklists, guides and generated pages |
| `memory` | What the assistant remembers, and how to change it |
| `files` | Attachments, your files, sharing and sending |
| `tasks` | Watching and stopping work |
| `menu` | Docs links and the menu of deeper topics |

## Menu

At the `menu` step, offer the topics below as a short list and let the person
pick one, or say "next" to go through them in order. Show administrator topics
only to administrators (see "Fit The Tour To The Person"). Read the matching
reference before sending a topic.

Administrator topics, from [admin-steps.md](references/admin-steps.md):

| Topic id | Topic |
|---|---|
| `admin_people` | Adding people, roles, disabling and removing |
| `admin_keys` | The team's model keys, sign-in apps and shared accounts |
| `admin_grow_team` | New specialists, team skills and new services |
| `admin_access` | Team-wide access, blocks and internet access |
| `admin_status` | The Status page |

Topics for everyone, from [more-topics.md](references/more-topics.md):

| Topic id | Topic |
|---|---|
| `access_page` | The Access page and how much the team lead may do without asking |
| `more_chat_apps` | Using more than one chat app |
| `own_model` | Your own model or model key |
| `workflows_page` | The Workflows page |
| `appearance` | **Web Chat only.** Theme and animation |
| `voice` | Voice messages |

When the menu is finished, or the person chooses to stop, close with one line
pointing to the docs and saying they can ask about any topic at any time.

## Keep Claims Accurate

- Mention a tool, sign-in or command only when it fits the person: GitHub,
  Google and X sign-ins are personal; team-wide setup is for administrators.
- Use the commands exactly as the references give them. If the person asks
  about something the references do not cover, check `/help` output or the
  docs instead of guessing.
- Never ask for a password, token or key in chat. Point to `/link` or `/auth`,
  which open a secure form.
- Describe what happens, not internal names: say "an administrator approves it
  in the Inbox", not tool or service names.

## Record Progress

When the user says `finish`, `stop`, `end`, `cancel`, `pause the guide`, or
otherwise ends the tour:

1. Identify the last completed step or topic id.
2. Call `memory(action="list", bank="usermem")` when available and look for
   an existing fact tagged `onboarding_guide`.
3. If one exists, call `memory(action="replace", bank="usermem", memory_id=...)`
   with the updated fact. Otherwise call
   `memory(action="create", bank="usermem", fact_text=...)`.
4. Use fact text like:
   `Onboarding guide progress: completed through step_id; resume at next_step_id.`
5. Include metadata when supported:
   `{"kind":"onboarding_guide_progress","completed_section":"step_id","resume_section":"next_step_id"}`
6. Tell the user briefly that the guide is stopped and can resume later.

When resuming, inspect `usermem` first and continue from `resume_section`. If
the saved id is not a step or topic id in this guide, the tour has changed
since it was saved: say so and offer to start from the beginning. If memory
tools are unavailable, continue from the most likely next step based on the
current conversation and say that progress could not be saved automatically.

## Tone

- Keep each message compact and concrete.
- Use the assistant name naturally, without repeating it unnecessarily.
- Include one or two tasteful emoji per step when they improve scanning or
  warmth.
- Avoid implementation jargon unless the user asks for details.
- Use examples that the user can copy directly into chat.
