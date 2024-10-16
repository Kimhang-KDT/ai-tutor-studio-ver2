# AI Tutor Studio

AI Tutor Studio는 영어 모의고사 문제에 대한 AI 기반 튜터링 시스템입니다.

## 프로젝트 구조

- `client`: React 기반의 프론트엔드
- `server`: FastAPI 기반의 백엔드

## 시작하기

### 클라이언트 실행

npm start

server 실행 명령어

python -m uvicorn main:app --host 0.0.0.0 --reload

## 주요 기능

1. 문제 관리
   - 모의고사 문제 목록 조회
   - 문제별 상세 정보 및 답안 입력

2. AI 모델 관리
   - 난이도별 (Low, Medium, High) 파인튜닝 모델 생성
   - 모델 상태 모니터링

3. 답변 생성 및 테스트
   - AI 모델을 통한 답변 생성
   - 생성된 답변과 표준 답안 비교 테스트

4. 음성 인식
   - 음성을 텍스트로 변환하여 답안 입력 지원

## 데이터베이스 구조

- `questions`: 문제 정보
- `base_answer`: 기본 답안
- `low_answer`, `medium_answer`, `high_answer`: 난이도별 답안
- `llm_models`: AI 모델 정보

## 개발 참고사항

- MongoDB 로컬 덤프 명령어: `mongodump --host 127.0.0.1 --port 27017`
- 환경 변수 설정: `.env` 파일에 필요한 API 키와 데이터베이스 정보 설정

## 향후 계획

- 학생 레벨 관리 기능 추가
- 성능 최적화 및 사용자 경험 개선
- 다국어 지원

## 기여하기

프로젝트에 기여하고 싶으시다면, 이슈를 열거나 풀 리퀘스트를 보내주세요.
