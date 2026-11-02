# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis([str(root / 'reader_desktop_20261102.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root / 'reader_ui.html'), '.'),
                        (str(root / 'assets' / 'wenyu.ico'), 'assets')],
    hiddenimports=['markdown.extensions.tables', 'markdown.extensions.fenced_code',
                   'markdown.extensions.toc', 'markdown.extensions.sane_lists',
                   'webview.platforms.winforms', 'webview.platforms.edgechromium'],
    hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='文阅_md阅读器',
          icon=str(root / 'assets' / 'wenyu.ico'),
          debug=False, strip=False, upx=True, console=False)
