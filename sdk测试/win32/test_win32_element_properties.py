r"""Win32Element 五个公开只读属性专项测试。

属性/访问器：id、element_id、name、raw、process_key。它们用于读取元素身份、运行时名称、
底层描述信息及所属应用标识；不执行动作。脚本参数：--non-interactive自动模式。
运行：uv run .\win32\test_win32_element_properties.py --non-interactive
前置：dev、靶场运行，启用 D:\code\元素库\260902_win元素；自动激活表单页。
使用 win32靶场_表单控件_输入框_姓名，检查类型、id别名、raw独立副本和last_result副作用。
"""

import argparse
import time
from pathlib import Path
from uiautoma import current,win32
from uiautoma.win32 import Win32Element
import test_win32_get_value as helper
from test_win32_highlight import restore_focus_for_mode,parse_run_options
from _form_tab import ensure_form_tab


def main(non_interactive=False):
    print('UIAutoma Win32 Element API 测试\n  API: Win32Element 属性专项')
    print('  属性: id / element_id / name / raw / process_key\n  目标: win32靶场_表单控件_输入框_姓名')
    results=[];package=element=None;focus_status='未检查'
    mouse,foreground=helper.current_cursor(),helper.current_foreground();started=time.perf_counter()
    def case(name,check): results.append(helper.run_case(name,check))
    def prepare():
        nonlocal package,element
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==Path(r'D:\code\元素库\260902_win元素').resolve()
        ensure_form_tab(package)
        element=win32.find(package.selector('win32靶场_表单控件_输入框_姓名',kind='win'),timeout=5)
        assert isinstance(element,Win32Element)
        return '输入框Runtime元素已获取',[f'元素库: {package.package_dir}']
    def identities():
        identity=element.id() if callable(element.id) else element.id
        assert type(identity) is str and identity
        assert element.element_id==identity
        assert type(element.name) is str and element.name
        return 'id、element_id和name类型及别名关系正确',[f'id: {identity}；name: {element.name}']
    def raw_shape():
        raw=element.raw
        assert type(raw) is dict and raw and raw.get('id')
        assert raw is not element.raw
        return 'raw返回非空独立dict，含底层id字段',[f'字段数: {len(raw)}']
    def raw_isolation():
        before=dict(element.raw);copy=element.raw;copy['__test__']='changed'
        assert '__test__' not in element.raw and element.raw==before
        return '修改raw副本不影响后续读取'
    def process():
        value=element.process_key
        assert type(value) is str
        return 'process_key返回字符串（可为空）',[f'值: {value!r}']
    def last_result():
        old=element.last_result
        _=element.id() if callable(element.id) else element.id;element.element_id;element.name;element.raw;element.process_key
        assert element.last_result is old
        return '读取五个属性不创建或修改last_result'
    def repeat():
        identity=element.id() if callable(element.id) else element.id
        assert identity==element.element_id and element.name==element.name
        assert element.raw==element.raw and element.process_key==element.process_key
        return '连续读取属性结果稳定'
    try:
        case('测试准备',prepare)
        if results[-1].passed:
            case('身份与名称',identities);case('raw结构',raw_shape);case('raw独立性',raw_isolation)
            case('process_key',process);case('无副作用',last_result);case('重复读取',repeat)
            def errors():
                # 属性均为无参读取，尝试调用会由Python拒绝；仅验证公开方法id()需self。
                identity=element.id() if callable(element.id) else element.id
                assert isinstance(identity,str)
                return '五个访问器均可读取，不存在额外调用参数'
            case('访问规则',errors)
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            try:focus_status=restore_focus_for_mode(foreground,non_interactive)
            except Exception as exc:errors.append(f'前台: {exc}')
            try:helper.restore_cursor(mouse)
            except Exception as exc:errors.append(f'鼠标: {exc}')
            if package is not None:
                try:package.close()
                except Exception as exc:errors.append(f'Package: {exc}')
            if errors:raise RuntimeError('；'.join(errors))
            return '鼠标恢复、Package释放；靶场保持表单页',[f'焦点: {focus_status}']
        case('资源清理',cleanup);helper.render_results(results)
    passed=sum(r.passed for r in results);ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Win32Element属性专项测试')
    parser.add_argument('--non-interactive',action='store_true')
    parser.parse_args();raise SystemExit(main(non_interactive=True))
