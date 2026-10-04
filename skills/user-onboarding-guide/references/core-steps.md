# Core Tour Steps

Facts and example wording for each core step, in order. Adapt the wording to
the person and the chat app, and keep one step per message. Labels in **bold**
are the exact text people see in Web Chat.

## team

Explain that a small team works behind the assistant. The team lead answers
simple things directly and brings in specialists for bigger things, then pulls
the results together.

In Web Chat, add that the small triangle pattern at the bottom of the left
sidebar lights up when the team is working: gold for the team lead, a colour
for each busy specialist.

```text
🧭 Behind me is a small specialist team. For simple things, I answer directly. For bigger things, I bring in the right help (research, comparisons, personal admin, home projects, coaching) and pull the pieces back together for you.
```

## screen_map

**Web Chat only.** Give a quick map, then say each later step will point to
where its feature lives.

- Left sidebar: **New Chat** starts a fresh thread; your past threads are
  listed below it, each with a pencil to rename and a button to archive.
- The ⚙ **Settings** button at the top of the sidebar opens the tabs
  **Inbox**, **Access**, **Team**, **Tasks**, **Memories** and **Appearance**.
- Links under the Settings tabs: **Chat Alerts** (browser notifications),
  **Workspace** (your files), **Runtime** (objectives and schedules).
  Administrators also see **Status**.
- The 📎 button by the message box attaches files.

```text
🗺️ A quick map: **New Chat** and your past threads are on the left. The ⚙ **Settings** button opens your Inbox, Access, Team, Tasks, Memories and Appearance. Below those tabs are links to your files (**Workspace**) and your objectives and schedules (**Runtime**).
```

## tools

Explain tools as ways to take real action: web research, files, GitHub,
Google (Gmail, Calendar, Drive), X, and services the team adds. When a tool is
not set up yet, the assistant opens the sign-in or approval page itself, so
the person can just ask for what they want.

```text
🧰 With the right tools, I can go beyond conversation: **search the web and compare sources**, **work with your files**, **check your GitHub repos** or **help with Gmail and Calendar**. If a tool isn't set up yet, just ask anyway. I'll open the sign-in or approval page for you.
```

## sign_in

Explain that passwords and tokens never go in chat. Signing in opens a secure
page with a countdown; the assistant never sees the secret.

- `/link cli:github` signs in to GitHub in the browser.
- `/link cli:google` signs in to Google.
- `/link cli:x` signs in to X.
- `/auth` shows what you are signed in to, without showing any secret.

In Telegram and Discord, `/link` also offers a menu of tools.

```text
🔐 I will never ask you to paste a password or token into chat. To connect a service, use `/link cli:github`, `/link cli:google` or `/link cli:x`. Each opens a secure page with a short countdown, and your secret goes straight into protected storage. `/auth` shows what you're signed in to.
```

## inbox

Explain that agents ask before using a tool they do not have yet. The person
gets a request card and decides:

- **Approve**, approve reading only, or **Deny**.
- "Keep for later tasks" lets the agent keep the access, for a chosen time.

Where requests appear:

- Web Chat: the card shows in the chat, and every request waits in
  **Settings → Inbox** (the number on the tab counts what you can decide).
- Telegram and Discord: buttons in the chat (**Allow for this task**, **Allow
  and keep**, **Allow reading only**, **Deny**). The chat account must be
  linked to the person first.
- WhatsApp, Signal, iMessage: a link to the Inbox. Replying "yes" does not
  decide anything.

Also mention: requests for access you do not hold yourself go to an
administrator, and the Inbox also tells you when work gets stuck. If the
person finds the requests too frequent, say the `access_page` menu topic shows
how to let the team lead do more on its own.

```text
📥 Before I use something new on your behalf, I ask. You'll get a card where you can **approve**, **approve reading only** or **deny**, and tick **Keep for later tasks** so I don't have to ask again. Everything waiting is in **Settings → Inbox**, which also tells you if a task gets stuck.
```

## schedules

Explain reminders, scheduled tasks and recurring checks in plain words. Give
copyable examples:

- ⏰ **"Remind me when the show starts."**
- 🔎 **"Check this page every morning and tell me if it changes."**
- 📬 **"Follow up with me next Friday."**
- 🗓️ **"Every Monday at 8, send me my week's calendar."**

Then: `/schedules` lists them, and in Web Chat **Runtime → Schedules** pauses,
resumes or deletes them. Schedules run in the person's own time zone.

## objectives

Explain that an objective is a bigger goal the team keeps working on over
days or weeks, broken into tasks that can be retried without losing the goal.
The person starts one by asking:

- **"Make this an ongoing objective: get my home office set up by the end of
  the month."**
- **"Keep track of this as a goal: find a used car under $15k and send me the
  best options each week."**

Then: `/objectives` lists them, and in Web Chat **Runtime → Objectives** can
**Pause**, **Resume**, **Stop**, **Abandon** or **Delete** one.

```text
🎯 Some things take longer than one conversation. Say **"Make this an ongoing objective: …"** and the team keeps working toward it over days or weeks, retrying steps without losing the goal. `/objectives` lists them, and **Runtime → Objectives** lets you pause or stop one.
```

## pages

Explain that the assistant can turn messy goals into checklists, how-tos,
comparisons, articles or small interactive trackers, saved as pages the person
can reopen and ask to update.

- **"Make a comparison page of these three robot vacuums."**
- **"Give me a step-by-step how-to for patching drywall."**
- **"Build me a little tracker for my plant watering."**

Pages are saved in the person's own folder and listed at `/docs/sites/`.
Anyone with a page's link can open it, so keep private details out of pages.

## memory

Explain memory as getting to know the person over time: preferences,
recurring projects, household details, how they like answers framed. The
person can ask "What do you remember about me?" or say "Forget that".

- Web Chat: **Settings → Memories** has **Personal** and **Team** tabs. Each
  memory can be edited or deleted, and **New** adds one.
- Team memories are shared with everyone on the team; only administrators
  change them.

```text
🧠 I'll get to know you over time: your preferences, recurring projects, how you like decisions framed. Ask **"What do you remember about me?"** anytime. In **Settings → Memories** you can see, edit or delete each one yourself.
```

## files

- Attach files with 📎, by pasting, or by dragging them into the chat (Web
  Chat). Other chat apps accept attachments too.
- Web Chat: **Workspace** opens your own files. Select a file to preview it.
- **Share…** lets another person read or change one of your files or folders,
  for as long as you choose.
- **Send…** delivers a copy (or moves it) to a person, who approves it in
  their Inbox, or to the team's shared folder.
- In other chat apps, `/share <path> with <person>` and
  `/send <path> to <person>` do the same. Web Chat uses the buttons instead.

```text
📁 Drop files into the chat with 📎 or drag and drop, and I can read, convert or organize them. **Workspace** shows your own files. From there, **Share…** gives someone access and **Send…** delivers a copy to a person or the team folder.
```

## tasks

- Web Chat: **Settings → Tasks** shows what each agent is working on and what
  is queued, with **Stop and remove** and a list of **Finished tasks** with
  results.
- In any chat app, `/stop` lists active work and lets you cancel a task, the
  conversation's work, or everything.

## menu

Point to the docs: the overview at `/docs/` and the skills list at
`/docs/skills/`, built from the Web Chat base URL. Say they can also ask for a
short guide on any topic instead of reading everything. Then offer the menu
from SKILL.md.

```text
📚 That's the core tour! The full docs are at /docs/, and you can always ask me to explain one thing in a few lines. Want to go deeper on any of these?
- 🛡️ The Access page
- 💬 Using more than one chat app
- 🤖 Your own model or key
- 🗺️ The Workflows page
- 🎨 Theme and animation
- 🎙️ Voice messages
```

For an administrator, put the administrator topics first, under a short
"For running the team" heading.
