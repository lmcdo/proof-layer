"""A stand-in AI for tests: reads the prompt on stdin, answers every item yes, except value 7777 (no)."""
import json
import sys

text = sys.stdin.read()
body = text.split("\n\n", 1)[1]            # the items follow the instructions
items = json.loads(body)
print("Sure, here you go:")
print(json.dumps([{"id": i["id"], "answer": "no" if i["value"] == 7777 else "yes"} for i in items]))
