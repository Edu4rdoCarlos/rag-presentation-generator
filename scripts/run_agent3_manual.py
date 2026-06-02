import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.agents.documenter_critic import agent_3_documenter_reflection_node
from app.core.state import TestDocState


def _load_state(path: Path) -> TestDocState:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    state_fields = TestDocState.model_fields.keys()
    state_payload = {key: value for key, value in payload.items() if key in state_fields}
    return TestDocState(**state_payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run only Agent3 Documenter/Critic against a JSON state file."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to a JSON file with TestDocState fields.",
    )
    args = parser.parse_args()

    try:
        state = _load_state(args.input)
    except FileNotFoundError:
        print(f"Arquivo nao encontrado: {args.input}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"JSON invalido em {args.input}: {exc}")
        return 1
    except ValidationError as exc:
        print(f"Campos invalidos para TestDocState em {args.input}:")
        print(exc)
        return 1

    result = agent_3_documenter_reflection_node(state)
    last_log = result["reflection_logs"][-1] if result["reflection_logs"] else ""

    print("\n=== RESULTADO DA CRITICA ===")
    print(last_log)

    print("\n=== ITERACAO ===")
    print(result["reflection_iteration"])

    print("\n=== DOCUMENTO FINAL GERADO ===")
    print(result["final_documentation"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
