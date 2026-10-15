# Deeper Topics For Everyone

Offer these from the menu. One topic per message.

## access_page

- **Settings → Access** shows who has access to what, in four tabs:
  **By Agent Type**, **By Person**, **By Tool** and **Files**. Members see
  their own access; **Remove** takes away access you gave.
- **How much the team lead may do without asking you** is set at the top of
  **By Agent Type**, or in chat:
  - `/access profile careful`: it may read with your everyday tools, and
    asks before changing anything.
  - `/access profile trusted`: it may use your everyday tools and run code in
    its sandbox without asking; you get a notice each time.
  - `/access profile manual`: it asks for everything.
  - Until you choose, every access is asked for.
- The choice covers only your own work.

```text
🛡️ If you're getting more requests than you'd like, choose how much I may do on my own: `/access profile careful` lets me read with your everyday tools and ask before changes, `/access profile trusted` lets me act and just tell you. **Settings → Access** shows everything I can use for you.
```

## more_chat_apps

- The same team is reachable from Web Chat and from any chat app the team has
  set up (Telegram, Discord, WhatsApp, Signal, iMessage).
- To use another app as the same person: send `/user code` where you already
  chat, then send `/user link <code>` from the new app.
- `/user token "my laptop"` makes a Web Chat token for another browser.

## own_model

- `/auth model me` opens a secure page that tests and saves your own model
  key. Without a tick, the key is for a model service the team already uses.
  Tick **Use this as my model** to have all your work use the model you chose,
  even from a service the team does not use.
- Your own key is used only for your work, never shared, and never replaced
  by the team's key.

## workflows_page

When a task needs several things set up or approved, the chat shows a
**Your Access Plan** card. The Workflows page (`/workflows`, also **Open
Workflows** in the Inbox) lists each task's requests in one place, with
**Review Ready Requests** to approve or deny them together.

## appearance

**Web Chat only.** **Settings → Appearance**:

- **Color Theme**: dark metallic or diffuse light.
- **Customize Theme**: colours, lighting and motion of the background, with
  **Regenerate Mesh** for a new pattern; **Share settings** copies your theme
  so someone else can apply it.
- **Interface Animation** turns motion off.
- **Chat Alerts** (below the tabs) turns browser notifications on or off.

## voice

- In Telegram and Discord, voice messages are turned into text, so you can
  talk instead of type.
- The assistant does not join live voice calls.
