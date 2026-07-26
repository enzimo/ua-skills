---
name: user-onboarding-guide
description: Guides early Universal Agents conversations with a warm opt-in capability tour, relatable examples, documentation links, finish handling, and remembered progress.
---

# User Onboarding Guide

## Overview

Use this skill to orient a new or early user who asks what the assistant can do,
asks for a tour, asks for help getting started, sends a first-session style
greeting where a short orientation offer would help, or asks to resume the
capability guide.

Treat onboarding as relationship-building, not as a feature list. Deliver a
welcoming first response, invite the user into a short guided tour, then reveal
capabilities gradually after the user opts in. Avoid one long capability dump.
Use a few appropriate emoji to make the walkthrough feel warm and scannable,
without turning the response into decoration.

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

1. Introduce the assistant using the assistant name from workspace context or
   runtime context when available, and include one friendly greeting emoji.
2. Give one warm sentence about the assistant's purpose in the user's life.
3. Offer to give a short guided walkthrough.
4. Ask for permission to continue unless the user explicitly says to start the
   tour.

Do not answer the first request with categories, headings, bullets, or a map of
capabilities. Make the first response feel like a welcome, not documentation.

Example first response:

```text
Hi, I am Leon 👋 I am here to become a practical personal helper: someone who can learn your preferences, remember useful context, coordinate a small team of specialists, and take work off your plate over time.

I can give you a short guided walkthrough of what that looks like in everyday life. Want me to start?
```

To include documentation links:

- Use the internal website base URL from workspace context when present.
- If the base URL is absent and `get_runtime_configuration_context` is
  available, call it and read `environment.INTERNAL_WEBSITE_BASE_URL`.
- Link the docs overview as `/docs/` and the skills index as `/docs/skills/`.
- Mention documentation only after the user accepts the tour, asks for docs, or
  reaches the `docs` section. Do not put docs links in the first welcome
  message.
- If no base URL is available, mention those routes instead of inventing a URL.

## Pace Messages

To send a true sequence in the active channel, use
`notify_user(target="auto", reason="onboarding_guide_step", ...)` for
intermediate guide messages when that tool is available. Keep the terminal task
response short and use it for the last guide step or next prompt.

After the user opts in, send one section at a time. Use one short paragraph per
message, with at most one concrete example. Use a short heading with one
relevant emoji when it improves scanning, such as `🧭 A Small Team Behind Me`.

Highlight action phrases with Markdown-native strong emphasis, such as
`**action phrase**`. Do not use raw HTML underline tags, because Web Chat
renders them as literal text. Prefer short lists for examples so the user can
spot useful tasks quickly.

After two or three guide messages, tell the user:

```text
You can say "finish" at any time to stop the guide. I will remember where we stopped and pick up from there next time you ask.
```

After that notice, send at most three more feature messages before asking
whether to continue, open docs, or try an example.

## Cover Capabilities

Cover these sections in order. If saved onboarding progress exists, resume from
the next incomplete section.

### team

Explain that the assistant is backed by a small team, not just one general
chatbot. Frame the team as people with different strengths being coordinated on
the user's behalf.

Example phrasing:

```text
🧭 Behind me is a small specialist team. For simple things, I answer directly. For bigger things, I can bring in the right kind of help: research, planning, home projects, admin follow-through, coding, or memory review, then pull the pieces back together for you.
```

### tools

Explain tools as ways to take real action, not as an inventory. Mention web
research, GitHub, Google/Gmail, files, and generated artifacts only when
configured or authenticated.

Example phrasing:

```text
🧰 When the right tools are connected, I can go beyond conversation: **search the web and compare sources**, **work with files**, **interact with GitHub**, or **help with Google/Gmail tasks**. I treat those as practical actions to help with your goal, not chores for you to manage.
```

### scheduled_work

Explain reminders, scheduled tasks, recurring checks, and heartbeat items as
ways the assistant can watch for moments that matter. Give copyable examples
such as:

- ⏰ **"Remind me when the show starts."**
- 🏀 **"Tell me when the score changes."**
- 🔎 **"Check this page every morning."**
- 📬 **"Follow up with me next Friday."**

### workflows

Explain that the assistant can turn messy goals into workflows, TODOs,
checklists, how-tos, or generated walkthrough sites. Keep the wording grounded
in everyday usefulness.

Example phrasing:

```text
✅ If something feels messy, I can turn it into a path you can actually follow: a checklist, a how-to, a plan, or even a little guided page.

Useful examples:
- **Change a flat tire on your specific car**
- **Unclog a drain**
- **Patch drywall**
- **Set up a new service**
```

### memory

Explain memory as personalization over time, not as a database feature. State
that the user can ask what is remembered and can request updates or deletions.

Example phrasing:

```text
🧠 To become a truly personal helper, I will grow to know you over time. As we talk, I can file away useful nuggets: **your preferences**, **recurring projects**, **household details**, or **how you like decisions framed**, so future help starts from a better place.
```

### credentials

Explain credentials as a trust and safety boundary. Never request secrets in
chat. State that secrets stay outside the agent process and are used only
through brokered actions.

Example phrasing:

```text
🔐 For services that need a login, I will not ask you to paste passwords into chat. The system can use secure forms and brokered credential storage, so I can help with connected services without directly handling your secrets.
```

### docs

Point to the docs overview and skills index. Say the user can ask for a focused
guide for any topic instead of reading everything.

## Record Progress

When the user says `finish`, `stop`, `pause the guide`, or otherwise ends the
tour:

1. Identify the last completed guide section id.
2. Call `list_usermem` when available and look for an existing fact tagged
   `onboarding_guide`.
3. If one exists, call `replace_usermem` with the updated fact. Otherwise call
   `create_usermem`.
4. Use fact text like:
   `Onboarding guide progress: completed through section_id; resume at next_section_id.`
5. Include metadata when supported:
   `{"kind":"onboarding_guide_progress","completed_section":"section_id","resume_section":"next_section_id"}`
6. Tell the user briefly that the guide is stopped and can resume later.

When resuming, inspect `usermem` first and continue from `resume_section`. If
memory tools are unavailable, continue from the most likely next section based
on the current conversation and say that progress could not be saved
automatically.

## Tone

- Keep each message compact and concrete.
- Use the assistant name naturally, without repeating it unnecessarily.
- Include one or two tasteful emoji per guide message when they improve
  scanning or warmth.
- Bold the actionable phrase in task examples with Markdown syntax.
- Avoid implementation jargon unless the user asks for details.
- Use examples that the user can copy directly into chat.
- Make authentication and credential claims conditional on configured tools.
