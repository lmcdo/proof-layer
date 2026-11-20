# Prompt to give your AI

Paste this with your PDF (or after it has read the PDF), then add your question at the end.

---

Answer my question from the document only. Reply with a JSON list and nothing else. Give one entry for every number your answer states, including prior-year numbers and percentages:

```
[{"name": "what the number is, with its year or period", "value": 5845, "unit": "tCO2-e", "page": 12, "source_text": "..."}]
```

Rules:
- `value` is a plain number, as printed in the document. If you worked it out yourself (a sum, a share, a change), put `"derived": true` and give the printed numbers you used as their own entries.
- `page` is the page of the PDF where the number is printed.
- `source_text` is copied exactly, character for character, from that page: the line that holds the number plus its label. Never fix spelling or spacing.
- If the document does not give the number, do not guess. Leave that entry out and say nothing about it.

My question:
