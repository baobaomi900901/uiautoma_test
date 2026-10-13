import ast
import json
import sys
from pathlib import Path

root = Path.cwd().resolve()
sys.path.insert(0, str(root))
import main

expected = root / "element"
assert main.LIBRARY_DIR == expected, (main.LIBRARY_DIR, expected)
ast.parse((root / "main.py").read_text(encoding="utf-8"))
entries = {p.name for p in expected.iterdir()}
required = {"package.json", "elements.json", "images.json", "icon", "images", "screenshot", "snapshot"}
assert required <= entries, required - entries
assert not any((root / name).exists() for name in required), "Library files still exist at the example root"
catalog = json.loads((expected / "elements.json").read_text(encoding="utf-8-sig"))
manifest = json.loads((expected / "package.json").read_text(encoding="utf-8-sig"))
assets = [item for group in catalog["groups"] for item in group["elements"]]
assert len(assets) == 2
assert {item["name"] for item in assets} == {"城市（单选）", "城市（多选）选项"}
for item in assets:
    assert (expected / "snapshot" / f"{item['id']}.json").is_file()
    assert (expected / "screenshot" / f"{item['id']}.png").is_file()
    json.loads((expected / "snapshot" / f"{item['id']}.json").read_text(encoding="utf-8-sig"))
json.loads((expected / "images.json").read_text(encoding="utf-8-sig"))
print(json.dumps({"library_path": str(main.LIBRARY_DIR), "package_id": manifest["id"], "asset_count": len(assets), "asset_names": [item["name"] for item in assets], "resource_files_present": True, "script_import_and_syntax": "passed"}, ensure_ascii=False, indent=2))
