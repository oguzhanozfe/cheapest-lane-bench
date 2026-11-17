# Results

Quality is the mean per-item score in [0, 1]; a lane holds quality when it is within 0.05 of the best lane on that task. Cost is per 1,000 items. Lanes marked partial ran out of quota before every item was attempted; they are shown but not ranked.

## Recommendation

| Task | Cheapest lane that holds quality | Quality | Best lane | Best quality | Cost / 1k |
| --- | --- | --- | --- | --- | --- |
| extract | **qwen3.5-9b-local** | 0.97 | gemini-3.5-flash-lite | 1.00 | $0.0406 |
| triage-log | **gemini-3.5-flash-lite** | 0.92 | gemini-3.5-flash-lite | 0.92 | $0.6527 |
| diff-review | **gemini-3.5-flash-lite** | 0.97 | gemini-3.5-flash-lite | 0.97 | $0.4051 |
| summarize | **qwen3.5-9b-local** | 0.81 | gemini-3.5-flash-lite | 0.84 | $0.0391 |
| commit-message | **gemini-3.5-flash-lite** | 0.99 | gemini-3.5-flash-lite | 0.99 | $0.3030 |
| translate | **gemini-3.5-flash-lite** | 0.93 | gemini-3.5-flash-lite | 0.93 | $0.7346 |

## extract

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 1.00 (1.00-1.00) | 1.00 |  | 1.53 | 340/122 | $0.4073 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.97 (0.93-1.00) | 0.97 |  | 11.33 | 307/146 | $0.0406 | yes |
| nemotron-3.5-lightning-free | 12/12 (12 ok) | 0.75 (0.50-1.00) | 0.75 |  | 6.6 | 8522/751 | $0 | yes |
| gemini-3.8-flash | 3/12 (2 ok) partial | 0.67 (0.00-1.00) | 0.67 |  | 212.06 | 358/100 | $0.6454 |  |

## triage-log

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.92 (0.75-1.00) | 0.92 |  | 1.54 | 542/196 | $0.6527 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.76 (0.54-0.96) | 0.76 |  | 13.38 | 412/231 | $0.0486 | yes |
| nemotron-3.5-lightning-free | 12/12 (12 ok) | 0.42 (0.17-0.67) | 0.42 |  | 5.53 | 6965/955 | $0 | yes |

## diff-review

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.97 (0.92-1.00) | 0.97 |  | 0.93 | 621/88 | $0.4051 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.64 (0.39-0.89) | 0.64 |  | 25.76 | 465/82 | $0.0895 | yes |
| nemotron-3.5-lightning-free | 12/12 (12 ok) | 0.58 (0.33-0.81) | 0.58 |  | 20.36 | 8796/3351 | $0 | yes |

## summarize

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.84 (0.76-0.92) | 0.84 | (pending; quality = deterministic only) | 1.88 | 498/160 | $0.5492 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.81 (0.73-0.89) | 0.81 | (pending; quality = deterministic only) | 11.54 | 516/184 | $0.0391 | yes |
| nemotron-3.5-lightning-free | 3/12 (2 ok) partial | 0.45 (0.00-0.84) | 0.45 | (pending; quality = deterministic only) | 8.47 | 1668/1316 | $0 |  |

## commit-message

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.99 (0.96-1.00) | 0.99 | (pending; quality = deterministic only) | 1.19 | 527/58 | $0.3030 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.92 (0.81-1.00) | 0.92 | (pending; quality = deterministic only) | 6.99 | 507/62 | $0.0237 | yes |

## translate

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.93 (0.92-0.95) | 0.93 | (pending; quality = deterministic only) | 3.85 | 351/252 | $0.7346 | yes |
| qwen3.5-9b-local | 8/12 (8 ok) partial | 0.90 (0.86-0.93) | 0.90 | (pending; quality = deterministic only) | 11.56 | 384/235 | $0.0408 |  |

## Judge agreement

No outputs were graded by both judges.

## Lanes not measured

- **deepseek-flash**: API key present but the account has no balance (HTTP 402); not topped up for this run.
- **codex-luna (gpt-5.6-luna)**: Codex CLI present but the ChatGPT account was over its usage pressure line.
- **rtx-3090 qwen3.8:27b**: Remote GPU box was unreachable on the run date.
