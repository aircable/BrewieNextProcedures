#!/usr/bin/env python3
"""Validate BrewieNext procedure-program source and cross-file contracts."""

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[1]
RESERVED_TARGETS = {"next_phase", "complete", "done", "exit", "loops", "error_handler"}
PASSIVE_ACTIONS = {
    "notify_user", "wait_for_user_input", "log", "log_event", "wait",
    "set_counter", "increment_counter",
}


def load_yaml(path):
    with path.open(encoding="utf-8") as source:
        data = yaml.safe_load(source)
    if not isinstance(data, dict):
        raise ValueError("document root must be a mapping")
    return data


def schema_errors(data, schema, path):
    return [
        f"{path}: {'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in sorted(Draft7Validator(schema).iter_errors(data), key=lambda item: list(item.path))
    ]


def transition_target(rule):
    if not isinstance(rule, dict):
        return None
    if "then" in rule:
        return rule.get("then")
    if len(rule) == 1:
        return next(iter(rule.values()))
    return None


def action_error(action, devices, sensors, operations):
    if not isinstance(action, dict) or len(action) != 1:
        return "action must contain exactly one operation"
    kind, value = next(iter(action.items()))
    config = value if isinstance(value, dict) else {}
    if kind == "set_valve" and config.get("valve") not in devices["valves"]:
        return f"unknown valve {config.get('valve')!r}"
    if kind == "set_pump" and config.get("device") not in devices["pumps"]:
        return f"unknown pump {config.get('device')!r}"
    if kind in {"set_heater", "enable_pid", "disable_pid"} and config.get("device") not in devices["heaters"]:
        return f"unknown heater {config.get('device')!r}"
    if kind in {"read", "read_sensor"}:
        sensor = value if isinstance(value, str) else config.get("sensor")
        if sensor not in sensors:
            return f"unknown sensor {sensor!r}"
    if kind == "run_hop_stage" and "run_hop_stage" not in operations:
        return "run_hop_stage is not in the machine contract"
    if kind == "finish_avr_step_session" and config.get("operation") not in operations:
        return f"unknown operation {config.get('operation')!r}"
    known = PASSIVE_ACTIONS | {
        "set_valve", "set_pump", "set_heater", "enable_pid", "disable_pid",
        "read", "read_sensor", "run_hop_stage", "finish_avr_step_session",
    }
    if kind not in known:
        return f"unsupported action {kind!r}"
    return None


def validate(root=ROOT):
    errors = []
    procedure_schema = json.loads((root / "schemas/procedure.schema.json").read_text())
    workflow_schema = json.loads((root / "schemas/workflow.schema.json").read_text())
    catalog_schema = json.loads((root / "schemas/program-catalog.schema.json").read_text())
    machine = load_yaml(root / "contracts/brewie-b20.yml")
    devices = machine["devices"]
    sensors = set(machine["sensors"])
    operations = set(machine["operations"])
    package = load_yaml(root / "program-package.yml")
    entrypoints = package.get("entrypoints", {})
    for kind, value in entrypoints.items():
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if not isinstance(candidate, str) or not (root / candidate).is_file():
                errors.append(f"program-package.yml: {kind} entrypoint {candidate!r} does not exist")

    procedures = {}
    for path in sorted((root / "procedures").rglob("*.yml")):
        if ".backups" in path.parts:
            continue
        try:
            data = load_yaml(path)
        except (OSError, ValueError, yaml.YAMLError) as error:
            errors.append(f"{path.relative_to(root)}: {error}")
            continue
        relative = path.relative_to(root)
        errors.extend(schema_errors(data, procedure_schema, relative))
        name = data.get("name") or data.get("phase")
        if name != path.stem:
            errors.append(f"{relative}: name {name!r} must match filename {path.stem!r}")
        if name in procedures:
            errors.append(f"{relative}: duplicate procedure name {name!r}")
        procedures[name] = data
        states = data.get("states", {})
        start = data.get("start_state") or next(iter(states), None)
        if start not in states:
            errors.append(f"{relative}: start state {start!r} does not exist")
        for state_name, state in states.items():
            for section in ("action", "on_exit"):
                for index, action in enumerate(state.get(section, [])):
                    problem = action_error(action, devices, sensors, operations)
                    if problem:
                        errors.append(f"{relative}: {state_name}.{section}[{index}]: {problem}")
            for rule in state.get("transition", []):
                target = transition_target(rule)
                if target not in states and target not in RESERVED_TARGETS:
                    errors.append(f"{relative}: state {state_name!r} targets missing state {target!r}")

    workflows = {}
    for path in sorted((root / "workflows").glob("*.yml")):
        data = load_yaml(path)
        workflows[data.get("name")] = data
        relative = path.relative_to(root)
        errors.extend(schema_errors(data, workflow_schema, relative))
        node_ids = []
        for step in data.get("steps", []):
            branches = step.get("parallel", {}).get("branches", []) if "parallel" in step else [step]
            for branch in branches:
                node_ids.append(branch.get("id"))
                if branch.get("procedure") not in procedures:
                    errors.append(f"{relative}: unknown procedure {branch.get('procedure')!r}")
            if "parallel" in step:
                parallel = step["parallel"]
                branch_ids = {branch.get("id") for branch in branches}
                if parallel.get("primary") not in branch_ids:
                    errors.append(f"{relative}: parallel primary is not a branch")
                for required in parallel.get("join", {}).get("require", {}):
                    if required not in branch_ids:
                        errors.append(f"{relative}: join requires unknown branch {required!r}")
        duplicates = sorted({node for node in node_ids if node_ids.count(node) > 1})
        if duplicates:
            errors.append(f"{relative}: duplicate workflow node IDs {duplicates}")

    catalog_path = root / "catalog/programs.yml"
    catalog = load_yaml(catalog_path)
    errors.extend(schema_errors(catalog, catalog_schema, catalog_path.relative_to(root)))
    program_ids = [program.get("id") for program in catalog.get("programs", []) if isinstance(program, dict)]
    duplicates = sorted({program_id for program_id in program_ids if program_ids.count(program_id) > 1})
    if duplicates:
        errors.append(f"catalog/programs.yml: duplicate program IDs {duplicates}")
    for program in catalog.get("programs", []):
        if not isinstance(program, dict) or not program.get("workflow"):
            continue
        workflow = program.get("workflow")
        if workflow not in workflows:
            errors.append(
                f"catalog/programs.yml: program {program.get('id')!r} "
                f"references unknown workflow {workflow!r}"
            )
    return errors


def main():
    errors = validate()
    if errors:
        print("Procedure validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    count = len([
        path for path in (ROOT / "procedures").rglob("*.yml")
        if ".backups" not in path.parts
    ])
    print(f"Validated {count} procedures and {len(list((ROOT / 'workflows').glob('*.yml')))} workflow(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
