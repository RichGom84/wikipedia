# Wikipedia Search Summary MCP Server

검색어를 입력하면 위키피디아에서 관련 페이지를 찾고, 각 페이지의 첫 문단 요약을 묶어서 반환하는 Python FastMCP 서버입니다.

## 기능

- MCP tool 이름: `wiki_search_summary`
- 지원 언어: `ko`, `en`
- 기본 검색 개수: `10`
- 최대 검색 개수: `20`
- 위키피디아 공식 API 사용
- API 키 불필요
- 각 페이지 요약은 비동기 병렬 호출로 수집
- 일부 페이지 요약 호출 실패 시 해당 페이지만 건너뜀
- `User-Agent` 헤더 설정 지원

## 파일 구성

```text
.
├── server.py
├── requirements.txt
├── runtime.txt
├── render.yaml
└── README.md
```

## 설치

Python 3.10 이상이 필요합니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell에서는 다음처럼 실행할 수 있습니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 로컬 실행, stdio

Claude Desktop이나 Codex CLI에 연결할 때는 기본값인 `stdio` 전송을 사용합니다.

```bash
python server.py
```

Windows에서 `python` 명령이 없으면:

```powershell
py -3 server.py
```

## Claude Desktop 연결

`claude_desktop_config.json`에 아래처럼 추가합니다. `args`에는 이 프로젝트의 `server.py` 절대 경로를 넣어주세요.

```json
{
  "mcpServers": {
    "wiki-summary": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "WIKI_USER_AGENT": "WikiSummaryMCP/1.0 (contact: your-email@example.com)"
      }
    }
  }
}
```

Windows 예시:

```json
{
  "mcpServers": {
    "wiki-summary": {
      "command": "py",
      "args": ["-3", "C:\\Users\\Kwon\\Desktop\\vscode\\wikipedia\\server.py"],
      "env": {
        "WIKI_USER_AGENT": "WikiSummaryMCP/1.0 (contact: your-email@example.com)"
      }
    }
  }
}
```

## Tool 사용 예시

입력 파라미터:

```json
{
  "query": "서울",
  "lang": "ko",
  "limit": 10
}
```

응답은 사람이 읽기 좋은 마크다운 텍스트입니다.

```markdown
# '서울' 검색 결과 (10개)

## 1. 서울특별시
서울특별시는 대한민국의 수도이자 ...
[원문 보기](https://ko.wikipedia.org/wiki/서울특별시)
```

## Render 배포

MCP의 기본 `stdio` 전송은 로컬 앱이 프로세스를 직접 실행하는 방식이라 Render 같은 웹 호스팅에 그대로 노출하기 어렵습니다. 이 서버는 Render에서 띄우기 쉽도록 HTTP 기반 전송도 지원합니다.

Render Web Service 설정:

- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `python server.py`

환경 변수:

```text
MCP_TRANSPORT=streamable-http
HOST=0.0.0.0
WIKI_USER_AGENT=WikiSummaryMCP/1.0 (contact: your-email@example.com)
```

Render는 `PORT` 환경변수를 자동으로 제공합니다. 서버는 `PORT`가 있으면 해당 포트로 실행합니다.
`MCP_TRANSPORT`를 빼먹어도 Render의 `PORT` 환경변수를 감지해 자동으로 `streamable-http` 모드로 실행됩니다.
`HOST`를 빼먹어도 Render에서는 자동으로 `0.0.0.0`에 바인딩됩니다.

이 저장소에는 `render.yaml`도 포함되어 있어 Render Blueprint로 배포할 수도 있습니다. 배포 후 MCP HTTP 엔드포인트는 보통 아래 형식입니다.

```text
https://your-render-service.onrender.com/mcp
```

만약 사용하는 MCP 클라이언트가 SSE 전송만 지원한다면 환경 변수를 아래처럼 바꿔 실행할 수 있습니다.

```text
MCP_TRANSPORT=sse
```

## User-Agent 설정

위키미디어는 API 요청에 식별 가능한 User-Agent를 설정할 것을 권장합니다. 배포 시 아래 환경 변수를 본인 연락처로 바꾸는 것을 권장합니다.

```text
WIKI_USER_AGENT=WikiSummaryMCP/1.0 (contact: your-email@example.com)
```

## 구현에 사용한 위키피디아 API

검색:

```text
GET https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&srlimit={limit}&format=json&utf8=1
```

요약:

```text
GET https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}
```
