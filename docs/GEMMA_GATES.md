# Hosted Gemma Gate Results

Run: 2026-07-29T12:12:35.333095+00:00 · Model: `gemma-4-26b-a4b-it` · live run

| Gate | Status | Detail | Latency |
|---|---|---|---|
| text_smoke | PASS | ```json
{
  "reply": "I am ready. Please provide a photo of the catch and a list of candidate species to begin.",
  "rep | 39993 |
| image_smoke | PASS | ```json
{
  "reply": "I suggest this might be an Octopus, based on its reddish-brown skin texture and mantle shape, but  | 3524 |
| morisyen_text | PASS | ```json
{
  "reply": "I can help you identify fish species and record your catches.",
  "reply_morisyen": "Mo kapav ed o | 18338 |
| structured_output | PASS | ```json
{
  "reply": "I can help you identify your catch by suggesting species from a list you provide based on your pho | 19953 |
| function_call | PASS | requested get_marine_conditions | 3829 |
| tool_round_trip | PASS | ```json
{
  "reply": "The current marine conditions near Grand Baie show a wave height of 1.2m and a swell height of 1.8 | 6186 |
| timeout_handling | PASS | timeout raised and was caught cleanly |  |
| api_failure_handling | PASS | error raised and caught; dispatcher falls back to mock |  |
| latency_benchmark | PASS | median 18713 ms, min 17666, max 19680 | 18713 |
| thinking_comparison | WARN | thinking config not supported for gemma-4-26b-a4b-it; minimal-mode latency 28438 ms |  |
