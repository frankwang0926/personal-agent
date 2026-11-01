# personal-agent

A minimal Python personal agent with calculator, persistent memory, and task tools.

## Telegram

Set these values in your local, ignored `.env`:

```dotenv
OPENAI_API_KEY=your_openai_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USER_ID=your_numeric_personal_user_id
```

From the project directory, with your virtual environment active, run:

```bash
python telegram_bot.py
```

Send your bot a private message, such as “I need to call Pu”, then “I just called
Pu”. Only the configured owner can invoke the agent. The existing model and tools
are reused, so normal requests incur OpenAI API usage. Keep one bot process running
and avoid concurrent terminal-agent writes to the shared task/memory files.

Telegram conversations are saved separately in `telegram_conversation.json`.
Tasks and memory still use `tasks.json` and `memory.json`. All are ignored by Git.
Stop with Ctrl+C. Pending messages sent while offline are processed on restart.

### Interrupted requests

Before running the agent, the bot records the current update ID in
`telegram_inflight.json`. It saves conversation history, sends the reply, saves
the polling cursor, then clears the marker.

If processing is interrupted before checkpoint completion, startup blocks
automatic replay. A task write or reply may already have succeeded. Stop the bot
and inspect the pending update ID, Telegram conversation, and task state before
resolving it. Do not simply delete the marker and retry a task-changing request.
After inspection, resolution may mean skipping the already performed request by
checkpointing its ID plus one, or deliberately retrying after confirming no
effects occurred. Manual recovery is required in this version; there is no
automatic rollback or exactly-once guarantee. A marker for an update already
covered by the saved cursor is cleaned up automatically.

Unexpected model, storage, or delivery failures stop the process. Reaching the
agent's step limit sends an interruption notice and permits the next message.
Replies currently use one plain-text Telegram message; oversized replies can
fail delivery and enter the same manual recovery path.
