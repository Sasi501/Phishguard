import os, re, sys

# Root directory of the repository (two levels up from this script)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

PATTERNS = {
    "AWS Access Key ID": re.compile(r'AKIA[0-9A-Z]{16}'),
    "AWS Secret Access Key": re.compile(r'(?i)aws_secret_access_key[^\n]{0,40}'),
    "Generic API Key": re.compile(r'(?i)api[_-]?key[^\n]{0,40}'),
    "Auth Token": re.compile(r'(?i)auth[_-]?token[^\n]{0,40}'),
    "Password literal": re.compile(r'(?i)password[^\n]{0,40}'),
}

report_lines = ["# Secrets Audit Report", "", f"Scanned directory: {ROOT_DIR}", ""]

for dirpath, _, filenames in os.walk(ROOT_DIR):
    for filename in filenames:
        if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.exe', '.dll', '.so', '.bin')):
            continue
        file_path = os.path.join(dirpath, filename)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue
        for name, regex in PATTERNS.items():
            for match in regex.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                snippet = match.group(0).strip()
                rel_path = os.path.relpath(file_path, ROOT_DIR)
                report_lines.append(f"- **{name}** in `{rel_path}` line {line_num}: `{snippet}`")

if len(report_lines) == 4:
    report_lines.append("No secrets found.")

report = "\n".join(report_lines)

# Write report to the artifact directory (known path)
artifact_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'brain', 'd652a248-1263-4861-899c-bd5f21c4ffd2', 'secret_audit_report.md'))
os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
with open(artifact_path, 'w', encoding='utf-8') as out:
    out.write(report)
print(f"Secret audit report written to {artifact_path}")
