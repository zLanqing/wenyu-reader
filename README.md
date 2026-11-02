<p align="center"><img src="assets/wenyu.png" width="96" alt="文阅图标"></p>

# 文阅 · Markdown 阅读器

用于 Windows 的本地 Markdown 阅读器。支持含配图的文档、章节目录、公式、全屏放映、页面缩放、激光指示、高亮与手写笔迹。

## 下载与运行

在 [Releases](https://github.com/zLanqing/wenyu-reader/releases) 下载 `文阅_md阅读器.exe`，双击运行，无需安装 Python，也无需将源码放在 EXE 旁边。

运行条件：

- Windows 10/11，64位。当前发布包为 Windows x64 构建。
- 已安装 [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)。许多电脑已有；缺少时需安装。
- 数学公式使用联网加载的 MathJax。正文、本地图片及批注操作不依赖 MathJax 网络连接。

程序以单文件 EXE 分发，启动时会在系统临时目录解压内置运行组件，因此首次启动可能稍慢。

## 打开文档

- **MD 文件**：配图路径相对于 `.md` 所在目录解析，支持中文和空格。
- **文件夹**：顶层需有且仅有一份 `.md`，配图保留原来的相对位置。
- **ZIP**：包内需有且仅有一份 `.md`，可含其相对路径配图。

例如：

```text
报告/
├── 汇报.md
└── assets/
    └── figure.png
```

Markdown 写法：`![图示](assets/figure.png)`。EXE 不包含使用者的论文或文档；分享报告时请同时分享文档与配图，或导出含图片 HTML。

## 汇报与批注

| 操作 | 用法 |
|---|---|
| 进入放映 | F5，或点击“放映” |
| 退出放映 | Esc |
| 页面放大/缩小 | Ctrl＋鼠标滚轮；也支持 Ctrl＋加号/减号 |
| 恢复100% | Ctrl＋0 |
| 激光指示点 | 放映时按 L 开关；不留下轨迹 |
| 手写画笔 | 放映时按 P 开关，按住鼠标左键拖动留红色笔迹 |
| 高亮或标红 | 关闭画笔与激光指示，选中文字，在浮动菜单选择 |
| 撤销批注/笔迹 | Ctrl＋Z，最多保留本次阅读的20步 |
| 清除笔迹 | 鼠标移到右上角，在放映工具中操作；可撤销 |
| 查看大图 | 关闭画笔后点击正文图片 |

手写画笔用于正文与内嵌图片，图片放大弹窗不是绘图画布。放映工具在鼠标移至右上角时显示，移开后自动隐藏。

## 数据与网络

- 文档由本机读取服务加载，服务只绑定 `127.0.0.1`，每次启动使用随机地址，不向局域网提供服务。
- 桌面批注保存于 `%LOCALAPPDATA%\WenyuReader\annotations`，不会改写原始 Markdown。文档路径或正文变化后，旧批注不会自动套用到新内容。
- 导出 HTML 会包含当前批注、手写笔迹和内嵌本地配图，便于分享。批注不会仅随 EXE 自动传给他人。
- 公式组件从 jsDelivr 加载 MathJax；文档中的远程图片和外链也可能访问网络。阅读器没有将本地报告上传到 GitHub 的功能。

## 从源码运行

推荐在 Windows 上使用 Python 3.11：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe reader_desktop_20261102.py
```

也可以传入 Markdown 路径：

```powershell
.\.venv\Scripts\python.exe reader_desktop_20261102.py "examples\示例.md"
```

## 构建单文件 EXE

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm wenyu.spec
```

输出位于 `dist\文阅_md阅读器.exe`。`wenyu.spec` 同时嵌入界面、应用图标和 Python 运行依赖。构建仍依赖系统 WebView2，未将 WebView2 安装包捆入 EXE。

## 验证

```powershell
python -m unittest test_reader_app.py
```

当前测试覆盖本地图片、中文及空格路径、缺失/空图片提示、文件夹选择、ZIP 与远程图片处理。界面功能另经 Edge 与 WebView2 本机验证；不宣称已在所有 Windows 环境测试。

## 项目文件

| 文件 | 用途 |
|---|---|
| `reader_app.py` | Markdown 解析、图片嵌入、本机服务 |
| `reader_desktop_20261102.py` | WebView2 窗口、全屏与本机批注存储 |
| `reader_ui.html` | 阅读界面、缩放、文字批注与矢量画笔 |
| `assets/wenyu.ico` | 多尺寸 Windows 图标 |
| `assets/wenyu.svg`、`assets/wenyu.png` | 图标源与预览 |
| `wenyu.spec` | PyInstaller 单文件构建配置 |

图标由项目原有“文”字标识制作；项目使用 Python-Markdown、pywebview、PyInstaller 和 MathJax 等组件，各组件的许可归其权利人所有。本仓库尚未指定项目代码的开源许可证。
