# autocoin

## 설명
---
유튜버 조코딩의 ['비트코인 GPT 인공지능 AI 업비트 자동매매 시스템 만들기'](https://youtube.com/live/-7IVgjUw79s?feature=share)를 참고하여 만든 Repository입니다.



## How to use
---
### 가상 환경 구성
```
python3 -m venv .venv
```

### 가상 환경 활성화
```
source .venv/bin/activate
```

### 가상 환경에 패키지 설치
```
pip install -r requirements.txt
```

### 환경변수 파일에 API KEY 입력
- .env 파일 안에 키 입력
```
OPENAI_API_KEY=""
UPBIT_ACCESS_KEY=""
UPBIT_SECRET_KEY=""
SLACK_API=""
```

### 실행하기
```
python3 autotrade.py
```

### (종료하고 싶을 때) 가상 환경 비할성화
```
deactivate
```