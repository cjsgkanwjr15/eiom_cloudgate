# dump_project_for_prompt.py
# 프로젝트의 "텍스트 기반" 파일(코드/설정/문서)을 프롬프트용 포맷으로 UTF-8로 출력합니다.
# - 기본 포함: .py .html .css .js .ts .tsx .jsx .json .yml .yaml .toml .md .sql .ini .cfg .conf .sh .bat .ps1 .txt 등
# - 기본 제외: node_modules, .git, .venv, __pycache__, .next, dist 등
# - 바이너리(이미지/폰트 등)는 자동 스킵
# - 옵션: --include-dirs, --ignore-dirs, --ext, --all-text, --git, --output, --max-chars-per-part, --max-bytes

import argparse
import fnmatch
from pathlib import Path
import sys
import io
import subprocess
from typing import Optional, Set, List

# 표준출력을 UTF-8로(콘솔 출력 시 cp949 문제 방지). --output 쓰면 파일이 UTF-8로 저장됩니다.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 자주 제외하는 디렉터리(라이브러리/캐시/빌드 산출물)
DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "bower_components",
    "build",
    "dist",
    "out",
    "coverage",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".angular",
    # Windows 가상환경/라이브러리
    "Lib",
    "Scripts",
    "Include",
    "site-packages",
    # 자바/닷넷 등
    "target",
    "bin",
    "obj",
}

# 자주 제외하는 파일 패턴(로그/락파일/캐시 등)
DEFAULT_IGNORE_GLOB: List[str] = [
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*~",
    "*.log",
    ".DS_Store",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
]

# 기본으로 포함할 텍스트 파일 확장자(필요시 --ext로 덮어쓰기, --all-text로 무시)
DEFAULT_EXTS: Set[str] = {
    ".py",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".mjs",
    ".cjs",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".yml",
    ".yaml",
    ".md",
    ".markdown",
    ".sql",
    ".sh",
    ".bash",
    ".bat",
    ".ps1",
    ".txt",
    ".env.example",  # 예시는 허용
    ".jinja",
    ".j2",
}

# 바이너리 가능성이 높은 확장자는 스킵(이미지/폰트/압축 등)
BINARY_EXTS: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svgz",
    ".ico",
    ".bmp",
    ".tiff",
    ".psd",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    ".zip",
    ".rar",
    ".7z",
    ".gz",
    ".bz2",
    ".xz",
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".so",
    ".dll",
    ".dylib",
    ".bin",
}

# 코드블록 언어 매핑(마크다운 하이라이트용)
LANG_MAP = {
    ".py": "python",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".json": "json",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".sql": "sql",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".sh": "bash",
    ".bash": "bash",
    ".bat": "dos",
    ".ps1": "powershell",
    ".txt": "text",
    ".jinja": "jinja2",
    ".j2": "jinja2",
}


def choose_fence(content: str) -> str:
    # 코드 내용에 ```가 있으면 ~~~로 감싸 마크다운 깨짐 방지
    return "~~~" if "```" in content else "```"


def should_ignore(
    path: Path, extra_ignore_dirs: Set[str], ignore_glob: List[str]
) -> bool:
    # 디렉터리 이름 기준 제외
    all_ignores = DEFAULT_IGNORE_DIRS | extra_ignore_dirs
    for part in path.parts:
        if part in all_ignores:
            return True
    # 파일 패턴 기준 제외
    name = path.name
    for pat in ignore_glob:
        if fnmatch.fnmatch(name, pat):
            return True
    # .env와 비밀 파일은 기본 제외(예시는 허용)
    if name.startswith(".env") and name != ".env.example":
        return True
    return False


def is_binary_by_ext(p: Path) -> bool:
    return p.suffix.lower() in BINARY_EXTS


def looks_like_text(p: Path) -> bool:
    # 간단 텍스트 판별: 1) 널바이트 포함되면 바이너리로 간주 2) UTF-8로 부분 디코드 성공하면 텍스트로 간주
    try:
        with open(p, "rb") as f:
            chunk = f.read(2048)
        if b"\x00" in chunk:
            return False
        # 빠른 UTF-8 디코드 테스트
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


def read_text(p: Path) -> str:
    # UTF-8로 읽되 실패하면 대체 문자로
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def collect_candidates_by_git(root: Path) -> List[Path]:
    # git 추적 파일만 수집(깨끗하고, venv/빌드 산출물 대부분 제외됨)
    try:
        out = subprocess.check_output(
            ["git", "ls-files"],
            cwd=str(root),
            stderr=subprocess.DEVNULL,
        )
        rel_paths = out.decode("utf-8", errors="ignore").splitlines()
        return [root / rp for rp in rel_paths if rp.strip()]
    except Exception:
        return []  # git이 없거나 저장소가 아니면 빈 리스트


def collect_files(
    root: Path,
    include_exts: Optional[Set[str]],
    allow_all_text: bool,
    include_dirs: Optional[List[str]],
    extra_ignore_dirs: Set[str],
    ignore_glob: List[str],
    max_bytes: int = 0,
    use_git: bool = False,
) -> List[Path]:
    # 후보 목록 만들기: git 사용 여부에 따라 결정
    if use_git:
        candidates = collect_candidates_by_git(root)
        if not candidates:  # git 실패 시 rglob로 대체
            candidates = list(root.rglob("*"))
    else:
        candidates = list(root.rglob("*"))

    # include_dirs 전처리(상대 경로 prefix 비교)
    prefixes = None
    if include_dirs:
        prefixes = [d.strip("/\\") for d in include_dirs]

    files: List[Path] = []
    for p in candidates:
        if not p.is_file():
            continue
        if should_ignore(p, extra_ignore_dirs, ignore_glob):
            continue
        # include_dirs 제한(주어진 경로로 시작하는 파일만)
        if prefixes:
            rel_str = p.relative_to(root).as_posix()
            if not any(
                rel_str == pref or rel_str.startswith(pref + "/") for pref in prefixes
            ):
                continue

        # 파일 크기 제한
        if max_bytes and p.stat().st_size > max_bytes:
            continue

        # 확장자 / 텍스트 판정
        if allow_all_text:
            if is_binary_by_ext(p):
                continue
            if not looks_like_text(p):
                continue
        else:
            if include_exts is not None and p.suffix.lower() not in include_exts:
                continue

        files.append(p)

    files.sort(key=lambda x: x.relative_to(root).as_posix())
    return files


def build_tree(root: Path, files: List[Path]) -> str:
    lines = [f"{root.resolve().name}/"]
    for p in files:
        rel = p.relative_to(root).as_posix()
        lines.append(f"├─ {rel}")
    return "\n".join(lines)


def build_blocks(root: Path, files: List[Path]) -> List[str]:
    blocks = []
    for p in files:
        rel = p.relative_to(root).as_posix()
        ext = p.suffix.lower()
        lang = LANG_MAP.get(ext, "text")
        content = read_text(p)
        fence = choose_fence(content)
        block = f"=== file: {rel} ===\n{fence}{lang}\n{content}\n{fence}\n\n"
        blocks.append(block)
    return blocks


def make_parts(header_text: str, blocks: List[str], max_chars: int) -> List[str]:
    if max_chars <= 0:
        body = "".join(blocks)
        return [header_text + body + "[END FILES]\n"]
    parts: List[str] = []
    current = header_text
    for block in blocks:
        if len(current) + len(block) > max_chars and current != header_text:
            parts.append(current)
            current = "[FILES]\n"
        current += block
    current += "[END FILES]\n"
    parts.append(current)
    return parts


def main():
    ap = argparse.ArgumentParser(description="Dump project files for prompt (UTF-8)")
    ap.add_argument("--root", type=str, default=".", help="프로젝트 루트 폴더 경로")
    ap.add_argument(
        "--ext",
        type=str,
        nargs="*",
        default=None,
        help="포함할 확장자 목록(예: .py .html .css). 지정 안 하면 기본 셋 사용",
    )
    ap.add_argument(
        "--all-text",
        action="store_true",
        help="확장자 무시하고 '텍스트처럼 보이는' 모든 파일 포함(바이너리/이미지는 제외)",
    )
    ap.add_argument(
        "--include-dirs",
        type=str,
        nargs="*",
        default=None,
        help="루트 기준 이 경로들만 포함(예: src app pages public templates)",
    )
    ap.add_argument(
        "--ignore-dirs",
        type=str,
        nargs="*",
        default=[],
        help="추가로 제외할 디렉터리 이름/경로",
    )
    ap.add_argument(
        "--max-chars-per-part",
        type=int,
        default=0,
        help="각 파트 최대 문자 수(0이면 분할 안 함)",
    )
    ap.add_argument(
        "--max-bytes",
        type=int,
        default=0,
        help="이 바이트보다 큰 파일은 제외(0=무제한, 예: 200000)",
    )
    ap.add_argument(
        "--git",
        action="store_true",
        help="git 추적 파일만 포함(권장: 라이브러리/빌드 산출물 대부분 제외됨)",
    )
    ap.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 파일 경로(UTF-8 저장). 없으면 콘솔로 출력",
    )

    args = ap.parse_args()

    root = Path(args.root).resolve()
    # 확장자 셋 결정
    include_exts = None
    if not args.all_text:
        if args.ext:
            include_exts = {e if e.startswith(".") else f".{e}" for e in args.ext}
        else:
            include_exts = set(DEFAULT_EXTS)

    files = collect_files(
        root=root,
        include_exts=include_exts,
        allow_all_text=args.all_text,
        include_dirs=args.include_dirs,
        extra_ignore_dirs=set(args.ignore_dirs),
        ignore_glob=list(DEFAULT_IGNORE_GLOB),
        max_bytes=args.max_bytes,
        use_git=args.git,
    )

    overview = (
        "[PROJECT OVERVIEW]\n"
        f"- 이름: {root.name}\n"
        "- 목적/설명: <한두 문장으로 적으세요>\n"
        "- 실행 방법: <예: python main.py / npm run dev>\n"
        "- 언어/런타임: <예: Python 3.11, Node 18>\n"
        "- 주요 라이브러리/프레임워크: <예: Flask, FastAPI, React, Next.js>\n"
        "- 환경 변수: <PLACEHOLDER 사용, .env는 기본 제외됨>\n\n"
    )
    tree = build_tree(root, files)
    header = f"{overview}[PROJECT TREE]\n{tree}\n\n[FILES]\n"
    blocks = build_blocks(root, files)
    parts = make_parts(header, blocks, args.max_chars_per_part)

    if args.output:
        out_path = Path(args.output)
        # 여러 파트면 [PART i/N] 헤더를 붙여 저장
        text = "".join(
            (f"[PART {i}/{len(parts)}]\n" if len(parts) > 1 else "")
            + part
            + ("\n" if len(parts) > 1 else "")
            for i, part in enumerate(parts, 1)
        )
        out_path.write_text(text, encoding="utf-8")
    else:
        if len(parts) == 1:
            sys.stdout.write(parts[0])
        else:
            total = len(parts)
            for i, part in enumerate(parts, 1):
                sys.stdout.write(f"[PART {i}/{total}]\n")
                sys.stdout.write(part)
                sys.stdout.write("\n")


if __name__ == "__main__":
    main()
