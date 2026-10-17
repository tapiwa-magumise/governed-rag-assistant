"""Write data/aws.json from Terraform's outputs: the app role, the inference profiles and the guardrail versions."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
out = json.loads(subprocess.check_output(["terraform", f"-chdir={ROOT / 'terraform'}", "output", "-json"]))
cfg = {"app_role_arn": out["app_role_arn"]["value"], "profiles": out["profiles"]["value"],
       "guardrails": out["guardrails"]["value"]}
(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "aws.json").write_text(json.dumps(cfg, indent=1) + "\n")
print("wrote data/aws.json")
