# Continuous Runtime Operator Guide

Use Start Runtime, Stop Runtime, Pause, Resume, and Suspend from the UI. The status line reports lifecycle, health, resident model, active objective, inquiries, promotion candidates, Wikipedia budget, and recent initiative. Ask `What are you currently working on?` or `Which local model is available?` for grounded state.

## Recommended Pilot

Run a controlled operator pilot with the UI open. Exercise ordinary chat, context declarations, one Wikipedia lookup, a self-model question, a local model deepening request, pause/resume, suspend, restart, and review of pending promotion candidates.

## Reading Status

- `Runtime`: controller lifecycle state.
- `health`: controller health classification.
- `model`: resident model when known, otherwise default lane model.
- `objective`: active or waiting objective.
- `inquiries`: pending operator inquiry count.
- `promotions`: gated promotion candidate count.
- `wiki`: current session query count and budget.
- `initiative`: latest initiative outcome.

## Authority Reminder

DELTA can prepare and queue review items. It cannot persist, promote, commit, push, deploy, broaden web access, call providers, or change governance without operator authority.
