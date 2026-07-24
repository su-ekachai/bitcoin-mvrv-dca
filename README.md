# Bitcoin MVRV DCA Monitor

Daily job that reads Bitcoin's Market Value to Realized Value (MVRV) and
Short-Term Holder MVRV (STH-MVRV) on-chain ratios, classifies a dollar-cost
averaging (DCA) tier, and recommends a multiplier to apply to whatever base
amount the reader normally buys. It pushes an alert to Discord and/or
Telegram and appends the day's signal to a Google Sheet — it never computes
absolute amounts and never places trades. Source data lags realtime by one
to two days; each alert shows the data date it was computed from.

Indicator definitions and tier rationale: [docs/strategy.md](docs/strategy.md).
Full validation evidence: [docs/backtest-results.md](docs/backtest-results.md).

Daily guidance = `mvrv_mult × sth_mult`, a multiplier on the usual DCA buy:

| MVRV | Zone | mvrv_mult |
|---|---|---|
| < 1.0 | very cheap | 2.0 |
| 1.0 – 1.5 | cheap | 1.5 |
| 1.5 – 2.0 | normal | 1.0 |
| 2.0 – 2.5 | expensive | 0.5 |
| ≥ 2.5 | very expensive | 0 (stop) |

| STH-MVRV | sth_mult |
|---|---|
| < 0.9 | 1.5 |
| 0.9 – 1.0 | 1.25 |
| 1.0 – 1.1 | 1.0 |
| ≥ 1.1 | 0.5 |

## Strategy validation

Backtested against 2013–2026 daily data (`backtest.py` re-runs this against
the live API's history — it imports `classify()` from `dca_monitor.py`, so
the strategy under test is exactly the strategy that runs daily):

- Combined MVRV × STH-MVRV strategy beat uniform DCA on average cost basis by
  +29% (2018–21) and +20% (2022–26).
- Conflict rule (MVRV dominates: stop is stop) is empirically vacuous —
  MVRV > 2.5 ∧ STH-MVRV < 1.0 occurred on 0 of 4,947 days since 2013.
- Caveat: MVRV cycle-peak values have compressed across cycles
  (5.88 → 4.72 → 3.96 → 2.78). The fixed 2.5 "stop" threshold may never
  trigger again in future cycles. v1 keeps fixed thresholds and shows the
  MVRV percentile vs. the trailing 4 years in every alert so the compression
  stays visible; adaptive thresholds are future work — re-run `backtest.py`
  to justify before changing tier boundaries.

## Setup: GitHub Actions

1. Create a GitHub repo and push this project to it.
2. In the repo, go to **Settings → Secrets and variables → Actions** and add
   these **secrets**:
   - `DISCORD_WEBHOOK_URL`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `SHEETS_WEBHOOK_URL`
3. `.github/workflows/daily.yml` runs on a `43 0 * * *` cron (07:43
   Asia/Bangkok; the odd minute dodges GitHub's on-the-hour scheduling
   congestion) and can also be triggered manually via
   **Actions → daily-signal → Run workflow** (`workflow_dispatch`).
4. `.github/workflows/ci.yml` runs `ruff format --check`, `ruff check`, `ty
   check`, and `pytest` on every push and pull request.

Configure only the channels needed — any unset secret is skipped at runtime
with an INFO log line (see `dca_monitor.py`).

## Setup: Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`,
   and follow the prompts to get a bot token — this is
   `TELEGRAM_BOT_TOKEN`.
2. Send any message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and read
   `message.chat.id` from the JSON response — this is `TELEGRAM_CHAT_ID`.

## Setup: Discord webhook

1. In the target channel, open **Edit Channel → Integrations → Webhooks →
   New Webhook**.
2. Copy the webhook URL — this is `DISCORD_WEBHOOK_URL`.

## Setup: Google Sheet

1. Create a new Google Sheet.
2. Open **Extensions → Apps Script**, delete any boilerplate, and paste in
   the contents of `apps_script.gs`.
3. **Deploy → New deployment → Web app**: execute as **Me**, who has access
   **Anyone**. Deploy and authorize.
4. Copy the deployment URL — this is `SHEETS_WEBHOOK_URL`. The script
   creates (or reuses) a `signals` sheet and appends one row per run:
   `date, price, mvrv, sth_mvrv, tier, multiplier`.

## Raspberry Pi

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.14
git clone <repo> && cd bitcoin-mvrv-dca
crontab -e
# 30 7 * * * cd /home/pi/bitcoin-mvrv-dca && set -a && . ./.env && set +a && $HOME/.local/bin/uv run python dca_monitor.py >> monitor.log 2>&1
```

`.env` holds the same variables GitHub Actions gets as secrets (never commit it).
`monitor.log` grows unbounded over years; optionally add a logrotate rule or a
monthly `truncate` cron line.
