# Administrator Topics

Offer these only when the `Person you work for:` line says the person is an
owner or an administrator. One topic per message. The commands below are
refused for members, so never suggest them to a member.

## admin_people

Explain how to add people, then roles, then stopping someone's access.

- **Web Chat only person:** `/user invite --new "Alice" --label "Alice laptop"`
  returns a `/webchat` address and a one-time invitation code to give Alice.
  On first sign-in she makes her own permanent token.
- **Someone on Telegram, Discord, WhatsApp, Signal or iMessage:** send
  `/user <their id in that app> "Alice"` from that same app. The docs page
  `/docs/newuser/` explains how to find each app's id.
- **Model keys:** new people do not use the team's model keys unless the
  instance is set up that way, so their requests do not run until they add
  their own key (`/auth model me`). Add `--team-keys` when adding someone to
  let their work use the team's keys, or change it later with
  `/user team-keys <usr_id> on`.
- **Roles:** owner, admin, member. `/user role <usr_id> admin` changes a role.
  Only an owner makes or changes an owner, and the team always keeps at least
  one owner and one administrator.
- `/user list` shows everyone.
- **Stopping access:** `/user disable <usr_id>` is reversible and keeps their
  files and memory. `/user remove <usr_id>` ends their access at once and
  holds their data for 7 days, during which `/user restore <usr_id>` brings
  them back.

```text
👥 To add someone who'll use Web Chat, send `/user invite --new "Alice" --team-keys` and give her the address and one-time code it returns. For Telegram or Discord, send `/user <their id> "Alice"` from that app. `--team-keys` lets her work use the team's model keys; without it she'll need her own key first.
```

## admin_keys

- `/auth model` tests and saves the team's key for each model service the
  team uses. The key goes into protected storage, never into chat.
- `/auth google team_client` and `/auth x team_client` store the team's
  sign-in app for Google and X. People still sign in with their own accounts;
  storing the app gives nobody access by itself.
- `/link <tool> team` links a team account for tools that have one, such as
  `/link cli:x team`. Each person's own link is used first.
- `/auth` shows each key's state without showing the key.

## admin_grow_team

Explain that the team grows by asking, and every addition comes to an
administrator as one Inbox card to approve:

- **New specialist:** **"Create a specialist for tracking my investments."**
  A new specialist starts with no tools of its own.
- **Team skill:** give a public GitHub link to a skill. It is scanned before
  the approval card appears.
- **New service:** **"Connect to our Notion workspace."** The team lead picks
  the best way (a command-line tool, a web API or an MCP server) and puts
  everything needed on one card.

In Web Chat, **Settings → Team** lists the agents, their types and connected
MCP servers.

## admin_access

- Members decide access for their own work. Requests for access a person does
  not hold come to administrators.
- On the Access page (**Settings → Access**), administrators see everyone's
  access under **By Person** and can add blocks for a person, a role or the
  whole team.
- `/access block team internet --reason "Offline week"` turns internet access
  off for everyone; `/access unblock <id>` turns it back on.
- `/access requests` lists what you can decide.
- Bigger platform changes (settings, restarts, new specialists, team skills)
  are staged as an exact plan and wait in the Inbox for an administrator.

## admin_status

**Web Chat only** (otherwise give the link). **Status** below the Settings
tabs opens a page of **Problems**, **Warnings** and **Notes** about the
running team, such as a model key that stopped working or a stuck schedule.
"Nothing needs attention" means all is well. Suggest checking it when
something seems off.
