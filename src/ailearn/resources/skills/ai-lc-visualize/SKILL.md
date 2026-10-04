---
name: ai-lc-visualize
description: Explain an AI-LC learning topic with data plots, diagrams, interactive illustrations or generated images. Use when a visual representation helps understanding, comparing cases or exploring a misconception.
---

# Visual explanation

Read shared policy, Teacher instructions, profile and current brief. Pick one question
the visual should answer. Choose the simplest suitable representation:
- Quantitative facts: reproducible chart with a plotting tool available in the harness.
- Structure or steps: SVG, Mermaid, HTML or a diagram tool.
- Exploring parameters: an interactive visualization tool or a small standalone HTML.
- Intuition or illustration: an available image-generation/editing tool (such as image2),
  if the harness exposes it. Follow its own instructions and inspect its actual output.

Check available tools before promising an asset. A skill does not install plotting,
image or video services. If generation is unavailable, produce a code-native diagram
or explicit storyboard and explain the limitation. Never claim an image was generated
when only a prompt was written. Do not execute learner code to produce visuals.

Use real data with provenance or clearly labeled synthetic data. Check numbers, units,
axes and visual scaling; image tools are illustrations, not a numerical calculation engine.
Label symbols in the learner's language. Save reusable visuals under `materials/visuals/`
in the active course, preserve existing files, and show the artifact to the learner.
Ask the learner to predict or interpret a change. A visual explanation establishes exposure;
independent assessment uses a fresh representation and does not reuse the revealed answer.
