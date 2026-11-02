# -*- coding: utf-8 -*-
"""文阅：在本机浏览器中阅读 Markdown，配图随文档加载。"""
import base64
import html
import io
import json
import mimetypes
import os
import posixpath
import re
import secrets
import sys
import threading
import time
import webbrowser
import zipfile
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import markdown


def render_markdown(text):
    formulas = []

    def protect(match):
        formulas.append(match.group(0))
        return 'WENYUMATHPLACEHOLDER' + str(len(formulas) - 1) + 'END'

    text = re.sub(r'\$\$(.+?)\$\$', protect, text, flags=re.DOTALL)
    text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', protect, text)
    body = markdown.markdown(text, extensions=['tables', 'fenced_code', 'toc', 'sane_lists'])
    for i, formula in enumerate(formulas):
        body = body.replace('WENYUMATHPLACEHOLDER' + str(i) + 'END', html.escape(formula))
    return body


class ImageEmbedder(HTMLParser):
    def __init__(self, read_image):
        super().__init__(convert_charrefs=False)
        self.read_image = read_image
        self.parts = []
        self.images = 0
        self.embedded = 0
        self.warnings = []

    def handle_starttag(self, tag, attrs):
        if tag != 'img':
            self.parts.append(self.get_starttag_text())
            return
        self.images += 1
        attrs = dict(attrs)
        src = attrs.get('src', '')
        if not src.startswith(('http://', 'https://', 'data:')):
            try:
                data, mime = self.read_image(src)
                if not data:
                    raise ValueError('文件为空（0 字节）')
                attrs['src'] = 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')
                self.embedded += 1
            except (OSError, ValueError, KeyError) as exc:
                reason = '文件不存在或路径不匹配' if isinstance(exc, (OSError, KeyError)) else str(exc)
                self.warnings.append({'path': src, 'reason': reason})
                attrs['data-image-error'] = reason
                attrs['data-original-src'] = src
                attrs.pop('src', None)
        self.parts.append('<img' + ''.join(' ' + k + '="' + html.escape(v or '', quote=True) + '"' for k, v in attrs.items()) + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        self.parts.append('&#' + name + ';')


def make_document(text, name, source, read_image):
    embedder = ImageEmbedder(read_image)
    embedder.feed(render_markdown(text))
    return {'name': name, 'source': source, 'html': ''.join(embedder.parts),
            'characters': len(text), 'images': embedder.images,
            'embedded': embedder.embedded, 'warnings': embedder.warnings}


def _image_mime(name):
    mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    if not mime.startswith('image/'):
        raise ValueError('引用的文件不是支持的图片格式')
    return mime


def load_zip(data, name):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = {item.filename.replace('\\', '/'): item for item in archive.infolist() if not item.is_dir()}
        candidates = sorted(n for n in files if n.lower().endswith('.md') and not n.startswith('__MACOSX/'))
        if not candidates:
            raise ValueError('ZIP 中没有 Markdown 文件')
        if len(candidates) > 1:
            raise ValueError('ZIP 中有多份 Markdown，请解压后选择要阅读的 MD 文件')
        if sum(item.file_size for item in files.values()) > 512 * 1024 * 1024:
            raise ValueError('ZIP 解压内容超过 512 MB，请先解压后打开 Markdown')
        md_name = candidates[0]
        text = archive.read(files[md_name]).decode('utf-8-sig')

        def read_image(src):
            relative = unquote(urlsplit(src.replace('\\', '/')).path)
            image_name = posixpath.normpath(posixpath.join(posixpath.dirname(md_name), relative))
            return archive.read(files[image_name]), _image_mime(image_name)

        return make_document(text, Path(md_name).name, name + ' / ' + md_name, read_image)


def load_document(path):
    path = Path(path).resolve()
    if path.is_dir():
        candidates = sorted(path.glob('*.md'))
        if len(candidates) != 1:
            raise ValueError('该文件夹顶层需有一份 Markdown；有多份时请使用“选择 MD / ZIP 文件”')
        path = candidates[0]
    if path.suffix.lower() == '.zip':
        return load_zip(path.read_bytes(), path.name)
    if path.suffix.lower() != '.md':
        raise ValueError('请选择 .md 文件、.zip 压缩包或含配图的文件夹')
    text = path.read_text(encoding='utf-8-sig')

    def read_image(src):
        parsed = urlsplit(src.replace('\\', '/'))
        if parsed.scheme:
            raise ValueError('请使用相对于 Markdown 的本地图片路径')
        image_path = (path.parent / unquote(parsed.path)).resolve()
        return image_path.read_bytes(), _image_mime(image_path.name)

    return make_document(text, path.name, str(path), read_image)


def choose_document(folder=False):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    try:
        if folder:
            return filedialog.askdirectory(parent=root, title='选择包含 Markdown 和 assets 的文件夹')
        return filedialog.askopenfilename(parent=root, title='选择 Markdown 或 ZIP',
                                         filetypes=[('Markdown / ZIP', '*.md *.zip'), ('所有文件', '*.*')])
    finally:
        root.destroy()


class ReaderServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, initial_path=None):
        self.token = secrets.token_urlsafe(24)
        self.document = load_document(initial_path) if initial_path else None
        self.last_seen = time.monotonic()
        self.dialog_lock = threading.Lock()
        resource_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
        self.page = (resource_dir / 'reader_ui.html').read_bytes()
        super().__init__(('127.0.0.1', 0), ReaderHandler)
        self.timeout = 1

    @property
    def url(self):
        return 'http://127.0.0.1:' + str(self.server_port) + '/' + self.token + '/'


class ReaderHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, data, content_type='application/json; charset=utf-8', status=200):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def route(self):
        # 每个实例仅接受自身随机地址和同源请求。
        prefix = '/' + self.server.token + '/'
        origin = self.headers.get('Origin')
        if not self.path.startswith(prefix) or (origin and origin != self.server.url.split('/' + self.server.token)[0]):
            self.respond({'error': '地址已失效，请重新打开阅读器'}, status=403)
            return None
        self.server.last_seen = time.monotonic()
        return self.path[len(prefix):].split('?', 1)[0]

    def do_GET(self):
        route = self.route()
        if route is None:
            return
        if route == '':
            self.respond(self.server.page, 'text/html; charset=utf-8')
        elif route == 'api/document':
            self.respond(self.server.document)
        elif route == 'api/ping':
            self.respond({'ok': True})
        else:
            self.respond({'error': '未找到页面'}, status=404)

    def do_POST(self):
        route = self.route()
        if route is None:
            return
        if route != 'api/open':
            self.respond({'error': '未找到操作'}, status=404)
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length < 1024:
                raise ValueError('请求格式不正确')
            action = json.loads(self.rfile.read(length)).get('action')
            if action not in ('file', 'folder'):
                raise ValueError('未知打开方式')
            if not self.server.dialog_lock.acquire(blocking=False):
                raise ValueError('文件选择窗口已经打开')
            try:
                path = choose_document(folder=(action == 'folder'))
                if not path:
                    self.respond({'cancelled': True})
                    return
                self.server.document = load_document(path)
                self.respond(self.server.document)
            finally:
                self.server.dialog_lock.release()
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            message = str(exc) if isinstance(exc, (ValueError, zipfile.BadZipFile)) else '无法读取文件，请检查文件是否完整、路径是否可用'
            self.respond({'error': message}, status=400)
        except Exception:
            self.respond({'error': '打开失败，请关闭文件选择窗口后重试'}, status=500)


def render_and_open(md_path=None):
    with ReaderServer(md_path) as server:
        webbrowser.open(server.url)
        # 浏览器关闭后，心跳停止，后台服务在三分钟内退出。
        while time.monotonic() - server.last_seen < 180:
            server.handle_request()
    return True


def main():
    try:
        render_and_open(sys.argv[1] if len(sys.argv) > 1 else None)
    except Exception as exc:
        import tkinter.messagebox
        tkinter.messagebox.showerror('文阅 · 打开失败', str(exc))


if __name__ == '__main__':
    main()
