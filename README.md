# A2A Projects

Agent2Agent (A2A) Protocol을 활용한 프로젝트입니다.

## 시작하기

### 처음 클론할 때 (서브모듈 포함)

```bash
git clone --recurse-submodules https://github.com/YOUR_USERNAME/a2a-projects.git
```

### 이미 클론한 경우 (서브모듈 초기화)

```bash
git submodule init
git submodule update
```

또는 한 번에:

```bash
git submodule update --init --recursive
```

### 서브모듈 최신 버전으로 업데이트

```bash
git submodule update --remote
```

## 프로젝트 구조

```
a2a-projects/
├── a2a-samples/          # A2A 샘플 코드 (서브모듈)
├── hello.py
├── pyproject.toml
└── README.md
```

## 서브모듈

| 이름 | 설명 | URL |
|------|------|-----|
| a2a-samples | A2A Protocol 샘플 및 데모 코드 | https://github.com/a2aproject/a2a-samples |

## 참고 자료

- [A2A Protocol 공식 사이트](https://a2a-protocol.org)
- [A2A Python SDK](https://github.com/a2aproject/a2a-python)
- [A2A Inspector](https://github.com/a2aproject/a2a-inspector)

