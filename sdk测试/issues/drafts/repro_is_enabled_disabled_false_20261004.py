r"""最小复现：现有原生 input 的 disabled='false' 仍应禁用。

运行：uv run .\issues\drafts\repro_is_enabled_disabled_false_20261004.py
只使用原元素库副本和新标签页，结束时恢复属性并清理。
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web'))
from _web_remaining_common import Context

__test__ = False


def main():
    context = Context('element.is_enabled')
    original = None
    changed = False
    try:
        if context.case('environment', '现有靶场与库副本可用', context.setup) == 'PASS':
            element = context.el()
            original = context.node('form-controls-native-text')['attrs'].get('disabled')
            context.js("root.getElementById('form-controls-native-text').setAttribute('disabled','false')")
            changed = True
            def check():
                dom = context.node('form-controls-native-text')
                result = element.is_enabled()
                actual = {'attribute': dom['attrs']['disabled'], 'dom_disabled': dom['disabled'],
                          'expected_is_enabled': not dom['disabled'], 'actual_is_enabled': result}
                print(json.dumps(actual, ensure_ascii=False), flush=True)
                return context.expect(result is (not dom['disabled']), actual)
            context.case('boolean_disabled_attribute', '属性存在即禁用，is_enabled() 应为 False', check)
    finally:
        if changed:
            context.js("(()=>{const e=root.getElementById('form-controls-native-text');if(args===null)e.removeAttribute('disabled');else e.setAttribute('disabled',args)})()", original)
        context.case('cleanup', '只关闭本次标签并删除库副本', context.cleanup)
    print(json.dumps(context.rows, ensure_ascii=True, indent=2))
    return 1 if any(row['status'] == 'FAIL' for row in context.rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
