# core/command_engine.py
import json
import hashlib
import copy
import subprocess
import os

FIXED_SEED = "WOWA_V2_FIXED"
LOG_FILE = "storage/audit_log.jsonl"

SCHEMA_V1 = {
    "version": "v1",
    "required": ["type", "payload"]
}

class CommandEngine:

    # ---------- STEP 1 ----------
    @staticmethod
    def parse(command: dict):
        return command

    # ---------- STEP 2 ----------
    @staticmethod
    def validate(command: dict):
        if command.get("version") != SCHEMA_V1["version"]:
            raise Exception("INVALID_VERSION")
        for k in SCHEMA_V1["required"]:
            if k not in command:
                raise Exception(f"MISSING_{k}")

    # ---------- STEP 3 ----------
    @staticmethod
    def deterministic_id(command: dict):
        raw = json.dumps(command, sort_keys=True) + FIXED_SEED
        return hashlib.sha256(raw.encode()).hexdigest()

    # ---------- STEP 4 ----------
    @staticmethod
    def log(entry: dict):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())

    # ---------- SNAPSHOT ----------
    @staticmethod
    def snapshot(command: dict):
        return json.loads(json.dumps(command))

    # ---------- TEST LAYERS ----------
    @staticmethod
    def test_ground_truth(cmd):
        if not isinstance(cmd, dict):
            raise Exception("GROUND_TRUTH_FAIL")

    @staticmethod
    def test_structural(cmd):
        if "type" not in cmd or "payload" not in cmd:
            raise Exception("STRUCTURAL_FAIL")

    @staticmethod
    def test_cross(cmd):
        if cmd["type"] == "deploy" and "git" not in cmd["payload"]:
            raise Exception("CROSS_REFERENCE_FAIL")

    @staticmethod
    def test_noise(cmd):
        noisy = copy.deepcopy(cmd)
        noisy["noise"] = "xxx"
        if CommandEngine.deterministic_id(noisy) == CommandEngine.deterministic_id(cmd):
            raise Exception("NOISE_FAIL")

    @staticmethod
    def test_contradiction(cmd):
        if "delete" in cmd["payload"] and "create" in cmd["payload"]:
            raise Exception("CONTRADICTION_FAIL")

    @staticmethod
    def run_tests(cmd):
        CommandEngine.test_ground_truth(cmd)
        CommandEngine.test_structural(cmd)
        CommandEngine.test_cross(cmd)
        CommandEngine.test_noise(cmd)
        CommandEngine.test_contradiction(cmd)

    # ---------- STEP 5 (ATOMIC) ----------
    @staticmethod
    def execute(command):
        # Nếu là lệnh tool (type="req") thì xử lý nội bộ qua wrapper
        if command.get("type") == "req":
            payload = command["payload"]
            tool = payload.get("tool")
            input_data = payload.get("input")

            # Lấy thông tin tool đã đăng ký
            from core.tool_registry import get_tool
            tool_spec = get_tool(tool)
            if not tool_spec:
                raise Exception(f"Tool '{tool}' not registered. Call /tool-register first.")

            cmd_template = tool_spec["command_template"]
            # Thay thế {input} bằng input_data
            cmd = cmd_template.format(input=input_data)

            # Thực thi wrapper
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Wrapper error: {result.stderr}")
            # Trả về output của wrapper
            return {"tool": tool, "input": input_data, "result": result.stdout.strip()}

        # Nếu là lệnh shell (type="deploy")
        else:
            result = subprocess.run(
                command["payload"],
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(result.stderr)
            return result.stdout

    # ---------- MAIN PIPELINE ----------
    @staticmethod
    def run(command: dict):
        # STEP 1
        cmd = CommandEngine.parse(command)

        # STEP 2
        CommandEngine.validate(cmd)

        # TESTS
        CommandEngine.run_tests(cmd)

        # STEP 3
        cid = CommandEngine.deterministic_id(cmd)

        # SNAPSHOT
        snap = CommandEngine.snapshot(cmd)

        # STEP 4 (LOG BEFORE EXEC)
        CommandEngine.log({
            "command_id": cid,
            "snapshot": snap,
            "status": "PENDING"
        })

        # STEP 5 (ATOMIC)
        try:
            output = CommandEngine.execute(cmd)

            CommandEngine.log({
                "command_id": cid,
                "status": "SUCCESS",
                "output": output
            })

            return {"command_id": cid, "output": output}

        except Exception as e:
            CommandEngine.log({
                "command_id": cid,
                "status": "FAILED",
                "error": str(e)
            })
            raise

    # ---------- REPLAY ----------
    @staticmethod
    def replay(command_id: str):
        with open(LOG_FILE) as f:
            logs = [json.loads(x) for x in f]

        for entry in logs:
            if entry.get("command_id") == command_id and "snapshot" in entry:
                return CommandEngine.run(entry["snapshot"])

        raise Exception("NOT_FOUND")