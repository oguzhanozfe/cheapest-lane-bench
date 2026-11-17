# Results

Quality is the mean per-item score in [0, 1]; a lane holds quality when it is within 0.05 of the best lane on that task. Cost is per 1,000 items. Lanes marked partial ran out of quota before every item was attempted; they are shown but not ranked.

## Recommendation

| Task | Cheapest lane that holds quality | Quality | Best lane | Best quality | Cost / 1k |
| --- | --- | --- | --- | --- | --- |
| extract | **qwen3.5-9b-local** | 0.97 | gemini-3.5-flash-lite | 1.00 | $0.0406 |
| triage-log | **gemini-3.5-flash-lite** | 0.92 | gemini-3.5-flash-lite | 0.92 | $0.6527 |
| diff-review | **gemini-3.5-flash-lite** | 0.97 | gemini-3.5-flash-lite | 0.97 | $0.4051 |
| summarize | **qwen3.5-4b-local** | 0.72 | groq-qwen3.8-27b | 0.78 | $0.0107 |
| commit-message | **groq-qwen3.8-27b** | 0.98 | groq-qwen3.8-27b | 0.98 | $0.6549 |
| translate | **qwen3.5-9b-local** | 0.85 | gemini-3.5-flash-lite | 0.89 | $0.0487 |

## extract

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 1.00 (1.00-1.00) | 1.00 |  | 1.53 | 340/122 | $0.4073 | yes |
| gemini-3.8-flash | 3/12 (3 ok) partial | 1.00 (1.00-1.00) | 1.00 |  | 103.16 | 351/142 | $0.7955 |  |
| groq-qwen3.8-27b | 12/12 (12 ok) | 1.00 (1.00-1.00) | 1.00 |  | 0.75 | 356/157 | $0.9111 |  |
| groq-gpt-oss-20b | 12/12 (12 ok) | 0.98 (0.95-1.00) | 0.98 |  | 0.48 | 414/156 | $0.0778 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.97 (0.93-1.00) | 0.97 |  | 11.33 | 307/146 | $0.0406 | yes |
| qwen3.5-4b-local | 12/12 (12 ok) | 0.89 (0.78-0.98) | 0.89 |  | 1.66 | 307/101 | $0.0062 | yes |
| nemotron-3.5-lightning-free | 12/12 (12 ok) | 0.75 (0.50-1.00) | 0.75 |  | 6.6 | 8522/751 | $0 | yes |

gemini-3.8-flash is partial (3 of 12 items). On the same items: gemini-3.8-flash 1.00, gemini-3.5-flash-lite 1.00, groq-gpt-oss-20b 0.96, groq-qwen3.8-27b 1.00, nemotron-3.5-lightning-free 0.67, qwen3.5-4b-local 0.84, qwen3.5-9b-local 0.93.

## triage-log

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | 3/12 (3 ok) partial | 1.00 (1.00-1.00) | 1.00 |  | 10.84 | 528/290 | $1.48 |  |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.92 (0.75-1.00) | 0.92 |  | 1.54 | 542/196 | $0.6527 | yes |
| groq-qwen3.8-27b | 12/12 (12 ok) | 0.89 (0.72-1.00) | 0.89 |  | 0.85 | 535/224 | $1.32 |  |
| qwen3.5-4b-local | 12/12 (12 ok) | 0.83 (0.58-1.00) | 0.83 |  | 3.12 | 412/224 | $0.0114 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.76 (0.54-0.96) | 0.76 |  | 13.38 | 412/231 | $0.0486 |  |
| groq-gpt-oss-20b | 12/12 (12 ok) | 0.64 (0.39-0.89) | 0.64 |  | 0.69 | 588/204 | $0.1052 |  |
| nemotron-3.5-lightning-free | 12/12 (12 ok) | 0.42 (0.17-0.67) | 0.42 |  | 5.53 | 6965/955 | $0 | yes |

gemini-3.8-flash is partial (3 of 12 items). On the same items: gemini-3.8-flash 1.00, gemini-3.5-flash-lite 1.00, groq-gpt-oss-20b 0.67, groq-qwen3.8-27b 1.00, nemotron-3.5-lightning-free 0.67, qwen3.5-4b-local 1.00, qwen3.5-9b-local 0.50.

## diff-review

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | 1/12 (1 ok) partial | 1.00 (1.00-1.00) | 1.00 |  | 5.59 | 569/68 | $0.6817 |  |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.97 (0.92-1.00) | 0.97 |  | 0.93 | 621/88 | $0.4051 | yes |
| groq-qwen3.8-27b | 12/12 (12 ok) | 0.94 (0.86-1.00) | 0.94 |  | 0.69 | 606/102 | $0.8928 |  |
| groq-gpt-oss-20b | 12/12 (12 ok) | 0.81 (0.58-1.00) | 0.81 |  | 0.66 | 670/148 | $0.0947 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.64 (0.39-0.89) | 0.64 |  | 25.76 | 465/82 | $0.0895 | yes |
| nemotron-3.5-lightning-free | 12/12 (12 ok) | 0.58 (0.33-0.81) | 0.58 |  | 20.36 | 8796/3351 | $0 | yes |
| qwen3.5-4b-local | 12/12 (12 ok) | 0.53 (0.29-0.78) | 0.53 |  | 2.61 | 465/211 | $0.0111 |  |

gemini-3.8-flash is partial (1 of 12 items). On the same items: gemini-3.8-flash 1.00, gemini-3.5-flash-lite 1.00, groq-gpt-oss-20b 1.00, groq-qwen3.8-27b 1.00, nemotron-3.5-lightning-free 0.00, qwen3.5-4b-local 0.27, qwen3.5-9b-local 1.00.

## summarize

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| groq-qwen3.8-27b | 12/12 (12 ok) | 0.78 (0.67-0.86) | 0.80 | 4.00 | 0.73 | 516/191 | $1.18 | yes |
| qwen3.5-4b-local | 12/12 (12 ok) | 0.72 (0.67-0.78) | 0.78 | 3.67 | 3.36 | 516/192 | $0.0107 | yes |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.72 (0.66-0.79) | 0.84 | 3.42 | 1.88 | 498/160 | $0.5492 |  |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.70 (0.63-0.76) | 0.81 | 3.33 | 11.54 | 516/184 | $0.0391 |  |
| nemotron-3.5-lightning-free | 2/12 (2 ok) partial | 0.68 (0.52-0.84) | 0.68 | not graded (partial lane) | 8.47 | 1668/1316 | $0 |  |
| gemini-3.8-flash | 2/12 (2 ok) partial | 0.68 (0.68-0.68) | 0.68 | not graded (partial lane) | 23.77 | 525/218 | $1.21 |  |
| groq-gpt-oss-20b | 12/12 (12 ok) | 0.59 (0.52-0.66) | 0.56 | 3.50 | 0.67 | 544/192 | $0.0984 |  |

nemotron-3.5-lightning-free is partial (2 of 12 items). On the same items: nemotron-3.5-lightning-free 0.68, gemini-3.5-flash-lite 0.63, groq-gpt-oss-20b 0.68, groq-qwen3.8-27b 0.76, qwen3.5-4b-local 0.69, qwen3.5-9b-local 0.63.

gemini-3.8-flash is partial (2 of 12 items). On the same items: gemini-3.8-flash 0.68, gemini-3.5-flash-lite 0.63, groq-gpt-oss-20b 0.68, groq-qwen3.8-27b 0.76, qwen3.5-4b-local 0.69, qwen3.5-9b-local 0.63.

## commit-message

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| groq-qwen3.8-27b | 12/12 (12 ok) | 0.98 (0.95-1.00) | 1.00 | 4.83 | 0.45 | 507/62 | $0.6549 | yes |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.92 (0.88-0.96) | 0.99 | 4.42 | 1.19 | 527/58 | $0.3030 | yes |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.86 (0.77-0.95) | 0.92 | 4.25 | 6.99 | 507/62 | $0.0237 | yes |
| groq-gpt-oss-20b | 12/12 (12 ok) | 0.76 (0.66-0.87) | 0.78 | 4.00 | 0.52 | 530/92 | $0.0673 |  |
| qwen3.5-4b-local | 12/12 (12 ok) | 0.70 (0.59-0.82) | 0.69 | 3.83 | 1.16 | 507/54 | $0.0037 | yes |

## translate

| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | Tokens in/out | Cost / 1k | Frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | 1/12 (1 ok) partial | 0.93 (0.93-0.93) | 0.93 | not graded (partial lane) | 10.8 | 332/193 | $0.9728 |  |
| gemini-3.5-flash-lite | 12/12 (12 ok) | 0.89 (0.86-0.93) | 0.93 | 4.42 | 3.85 | 351/252 | $0.7346 | yes |
| groq-qwen3.8-27b | 12/12 (12 ok) | 0.88 (0.83-0.92) | 0.92 | 4.33 | 1.01 | 367/256 | $1.32 |  |
| qwen3.5-9b-local | 12/12 (12 ok) | 0.85 (0.79-0.91) | 0.90 | 4.25 | 14.54 | 367/253 | $0.0487 | yes |
| groq-gpt-oss-20b | 12/12 (12 ok) | 0.80 (0.69-0.89) | 0.86 | 3.92 | 0.72 | 403/244 | $0.1036 |  |
| qwen3.5-4b-local | 12/12 (12 ok) | 0.80 (0.71-0.87) | 0.88 | 3.83 | 3.94 | 367/255 | $0.0131 | yes |

gemini-3.8-flash is partial (1 of 12 items). On the same items: gemini-3.8-flash 0.93, gemini-3.5-flash-lite 0.85, groq-gpt-oss-20b 0.92, groq-qwen3.8-27b 0.85, qwen3.5-4b-local 0.96, qwen3.5-9b-local 0.96.

## Judge agreement

20 outputs graded by both judges (claude-sonnet-5-5 (Claude Code subagent, rubric prompts from --dump) and gemini-3-flash-preview): exact agreement 5%, within one point 65%, Pearson r = 0.559, mean score 3.5 vs 4.8.

## Lanes not measured

- **deepseek-flash**: API key present but the account has no balance (HTTP 402); not topped up for this run.
- **codex-luna (gpt-5.6-luna)**: Codex CLI present but the ChatGPT account was over its usage pressure line.
- **rtx-3090 qwen3.8:27b**: Remote GPU box was unreachable on the run date.
