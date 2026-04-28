import json

with open("/opt/captacao-blindada/frontend/package.json", "r") as f:
    d = json.load(f)

d["dependencies"]["next"] = "15.3.6"
d["devDependencies"]["eslint-config-next"] = "15.3.6"

with open("/opt/captacao-blindada/frontend/package.json", "w") as f:
    json.dump(d, f, indent=4)

print("package.json updated to Next.js 15.3.6")
