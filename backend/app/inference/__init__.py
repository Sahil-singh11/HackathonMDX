"""Inference provider layer.

`base` defines the provider Protocol; `registry` selects and health-checks
providers; implementations live beside them (`gemma_hosted`, `gemma_local`).
The deterministic mock remains in `app.providers.mock` and is exposed here
through an adapter — it is a first-class, always-available, always-disclosed
provider, not an afterthought.
"""
