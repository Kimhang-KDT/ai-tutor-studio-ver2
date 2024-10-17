from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.database import init_db, get_questions_by_info, get_answers, db_get_datalists
from app.utils.utils import process_test_infos, save_or_update_answer, get_answer_status, get_specific_answer_from_db, test_finetuned_answers
from app.services.llm_service import create_finetuning_model, get_finetuning_status, create_finetuned_answers
from google.cloud import speech
import json
from google.oauth2 import service_account

# Google Cloud 인증 정보 설정
credentials_dict = json.loads(settings.GOOGLE_APPLICATION_CREDENTIALS)
credentials = service_account.Credentials.from_service_account_info(credentials_dict)

# Speech-to-Text 클라이언트를 생성합니다.
client = speech.SpeechClient(credentials=credentials)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        print("데이터베이스 초기화 성공")
    except Exception as e:
        print(f"데이터베이스 초기화 실패: {str(e)}")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://130.162.154.159:3002","https://test.atbot.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Tutor Studio API"}

@app.get("/test_infos")
async def get_test_infos_route():
    test_infos = await process_test_infos()
    return test_infos

@app.get("/questions/{test_id}/{subject_id}")
async def get_questions(test_id: str, subject_id: str):
    questions = await get_questions_by_info(test_id, subject_id)
    base_answers = await get_answers(test_id, subject_id, "base_answer")

    return questions, base_answers

@app.post("/questions/{test_id}/{subject_id}")
async def create_question():

    return {"message": "Question created successfully"}

@app.post("/answer/{test_id}/{subject_id}")
async def save_answer(test_id: str, subject_id: str, answer_data: dict):
    result = await save_or_update_answer(test_id, subject_id, answer_data)
    return result

@app.get("/answer_status/{test_id}/{subject_id}")
async def get_answers_status(test_id: str, subject_id: str):
    status = await get_answer_status(test_id, subject_id)
    return status

@app.get("/answer/{test_id}/{subject_id}/{question_num}/{answer_type}")
async def get_specific_answer(test_id: str, subject_id: str, question_num: str, answer_type: str):
    answer = await get_specific_answer_from_db(test_id, subject_id, question_num, answer_type)
    return {"answer": answer}

@app.get("/finetuning/datalists")
async def get_datalists():
    datalists = await db_get_datalists()
    return datalists

@app.post("/finetuning/{test_id}/{subject_id}/{level}")
async def create_finetuning_model_route(test_id: str, subject_id: str, level: str):
    result = await create_finetuning_model(test_id, subject_id, level)
    return result

@app.get("/finetuning_status/{job_id}")
async def get_finetuning_status_route(job_id: str):
    result = await get_finetuning_status(job_id)
    return result

@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    content = await audio.read()
    audio = speech.RecognitionAudio(content=content)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        sample_rate_hertz=48000,  # 클라이언트의 샘플 레이트와 일치시킵니다
        language_code="ko-KR",
    )

    response = client.recognize(config=config, audio=audio)

    text = ""
    for result in response.results:
        text += result.alternatives[0].transcript

    return {"text": text}

@app.get("/finetuned_answers/{test_id}/{subject_id}/{level}")
async def get_finetuned_answers(test_id: str, subject_id: str, level: str):
    result = await test_finetuned_answers(test_id, subject_id, level)
    return result

@app.post("/finetuned_answers/{model_id}/{level}/{test_id}/{subject_id}")
async def create_finetuned_answers_route(model_id: str, level: str, test_id: str, subject_id: str):
    result = await create_finetuned_answers(model_id, level, test_id, subject_id)
    return result
