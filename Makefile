.PHONY: setup test lint demo generate

setup:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check .

demo:
	MODE=cached uv run judgeops run configs/digital_minds.json
	MODE=cached uv run judgeops run configs/ai_control.json
	MODE=cached uv run judgeops export digital_minds --csv
	MODE=cached uv run judgeops export ai_control --csv

generate:
	MODE=live uv run judgeops run configs/digital_minds.json
	MODE=live uv run judgeops run configs/ai_control.json
