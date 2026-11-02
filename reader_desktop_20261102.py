# -*- coding: utf-8 -*-
"""文阅独立窗口版。复用现有阅读器，使用本机 WebView2 显示。"""
import sys
import threading
import os
import re
from pathlib import Path

import webview
import reader_app


class PresentationAPI:
    """同步页面放映状态与独立窗口的原生全屏状态。"""
    def __init__(self):
        self._window = None
        self._active = False
        self._lock = threading.Lock()

    def _annotation_path(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{8}', key):
            raise ValueError('无效的批注文档标识')
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        return base / 'WenyuReader' / 'annotations' / (key + '.html')

    def read_annotations(self, key):
        path = self._annotation_path(key)
        return path.read_text(encoding='utf-8') if path.exists() else ''

    def save_annotations(self, key, content):
        if not isinstance(content, str) or len(content) > 1000000:
            raise ValueError('批注内容过大')
        path = self._annotation_path(key)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix('.tmp')
            temporary.write_text(content, encoding='utf-8')
            temporary.replace(path)
        return True

    def set_presentation(self, active):
        if not isinstance(active, bool):
            raise ValueError('放映状态必须为布尔值')
        with self._lock:
            if active != self._active:
                self._window.toggle_fullscreen()
                self._active = active
            return self._active


def run_desktop(md_path=None):
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('zLanqing.WenyuReader')
    server = reader_app.ReaderServer(md_path)
    webview.settings['ALLOW_DOWNLOADS'] = True
    presentation_api = PresentationAPI()
    window = webview.create_window('文阅 · Markdown 阅读器', server.url,
                                   width=1280, height=900, min_size=(900, 650),
                                   text_select=True, background_color='#f1f5f5',
                                   js_api=presentation_api)
    presentation_api._window = window

    def choose_document(folder=False):
        options = {'dialog_type': webview.FileDialog.FOLDER if folder else webview.FileDialog.OPEN}
        if not folder:
            options['file_types'] = ('Markdown / ZIP (*.md;*.zip)', '所有文件 (*.*)')
        paths = window.create_file_dialog(**options)
        return paths[0] if paths else None

    original_chooser = reader_app.choose_document
    reader_app.choose_document = choose_document

    def ready():
        # DOI 等外链交给默认浏览器，阅读窗口保持在文档中。
        window.evaluate_js("""
            document.addEventListener('click', event => {
                const link = event.target.closest('a[href]');
                if (link && /^https?:/i.test(link.getAttribute('href'))) {
                    event.preventDefault(); window.open(link.href, '_blank');
                }
            });
        """)

    window.events.loaded += ready
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        icon = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets' / 'wenyu.ico'
        webview.start(gui='edgechromium', private_mode=True,
                      icon=str(icon) if icon.exists() else None,
                      localization={'global.quitConfirmation': '关闭文阅？'})
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        reader_app.choose_document = original_chooser


def main():
    try:
        run_desktop(sys.argv[1] if len(sys.argv) > 1 else None)
    except Exception as exc:
        import tkinter.messagebox
        tkinter.messagebox.showerror('文阅 · 启动失败',
            '无法打开独立阅读窗口。请确认已安装 Microsoft Edge WebView2 Runtime。\n\n' + str(exc))


if __name__ == '__main__':
    main()
