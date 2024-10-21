from app.core.config import settings
from openai import OpenAI
from app.utils.utils import create_finetuning_training_data
import asyncio
import tempfile
import os
import json
from app.db.database import save_llm_model, update_llm_model_status, get_system_prompt, get_questions_by_info, get_answers, save_level_answer

async def create_finetuning_model(test_id: str, subject_id: str, level: str):
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # 선택한 레벨의 트레이닝 데이터만 생성
    training_data = await create_finetuning_training_data(test_id, subject_id, level)

    try:
        # 트레이닝 데이터 로깅
        print(f"Training data for {test_id}-{subject_id}-{level}:")
        print(training_data[:1000])  # 처음 1000자만 출력
        
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.jsonl', encoding='utf-8') as temp_file:
            for line in training_data.split('\n'):
                temp_file.write(line + '\n')
            temp_file_path = temp_file.name
        
        print(f"Temporary file created at: {temp_file_path}")
        
        # 파일 내용 확인
        with open(temp_file_path, 'r', encoding='utf-8') as file:
            print("File contents:")
            print(file.read()[:1000])  # 처음 1000자만 출력
        
        # 파일 업로드
        with open(temp_file_path, 'rb') as file:
            file_response = client.files.create(
                file=file,
                purpose='fine-tune'
            )
        
        # 임시 파일 삭제
        os.unlink(temp_file_path)
        
        # 파인튜닝 작업 생성
        fine_tune_response = client.fine_tuning.jobs.create(
            training_file=file_response.id,
            model="gpt-4o-mini-2024-07-18",
            suffix=f"{test_id}_{subject_id}_{level}"
        )
        
        # 결과 저장
        result = {
            "status": fine_tune_response.status,
            "fine_tuned_model": fine_tune_response.fine_tuned_model,
            "job_id": fine_tune_response.id
        }

        # 데이터베이스에 저장
        await save_llm_model(
            test_id,
            subject_id,
            level,
            fine_tune_response.status,
            fine_tune_response.fine_tuned_model,
            fine_tune_response.id
        )

        # 상태 업데이트를 즉시 시작
        asyncio.create_task(update_model_status_periodically(fine_tune_response.id))

        return result

    except Exception as e:
        print(f"Error creating finetuning model: {str(e)}")
        print(f"Training data sample: {training_data[:500]}")  # 트레이닝 데이터 샘플 출력
        # 에러 발생 시 데이터베스에 실패 상태 저장
        await save_llm_model(
            test_id,
            subject_id,
            level,
            "failed",
            None,
            None
        )
        return {"error": str(e)}

async def update_model_status_periodically(job_id: str):
    while True:
        try:
            status = await get_finetuning_status(job_id)
            if status['status'] in ['succeeded', 'failed', 'cancelled']:
                break
            await asyncio.sleep(30)  # 1분마다 상태 확인
        except Exception as e:
            print(f"Error updating model status: {str(e)}")
            break

async def get_finetuning_status(job_id: str):
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        job = client.fine_tuning.jobs.retrieve(job_id)
        status = job.status
        if status == "validating_files":
            status = "validating_files"
        elif status == "queued":
            status = "pending"
        elif status in ["running", "succeeded", "failed", "cancelled"]:
            status = status
        else:
            status = "unknown"

        result = {
            "status": status,
            "fine_tuned_model": job.fine_tuned_model,
            "job_id": job.id
        }
        # 데이터베이스 업데이트
        await update_llm_model_status(job_id, status, job.fine_tuned_model)
        return result
    except Exception as e:
        print(f"Error getting finetuning status: {str(e)}")
        return {"error": str(e)}

async def create_finetuned_answers(model_id: str, level: str, test_id: str, subject_id: str):
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    system_prompt = await get_system_prompt(level)
    prompt = "문제의 풀이를 작성해줘"
    
    questions = await get_questions_by_info(test_id, subject_id)
    base_answers = await get_answers(test_id, subject_id, "base_answer")
    
    # question_num을 기준으로 정렬
    questions.sort(key=lambda x: x["question_number"])
    base_answers.sort(key=lambda x: x["question_num"])
    
    try:
        for question, base_answer in zip(questions, base_answers):
            if str(question["question_number"]) != base_answer["question_num"]:
                print(f"Warning: Question number mismatch. Question: {question['question_number']}, Answer: {base_answer['question_num']}")
                continue
            
            response = client.chat.completions.create(
                model=model_id,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": question["question"]},
                    {"role": "system", "content": question["content"]},
                    {"role": "system", "content": "\n".join(question["choices"])},
                    {"role": "system", "content": base_answer["answer"]},
                    {"role": "user", "content": prompt},
                ],
            )
            
            finetuned_answer = response.choices[0].message.content
            
            await save_level_answer(test_id, subject_id, level, {
                "question_num": question["question_number"],
                "answer": finetuned_answer,
                "test_month": question["test_month"],
                "subject_name": question["subject_name"]
            })
        
        return {"status": "completed"}
    except Exception as e:
        print(f"Error creating finetuned answers: {str(e)}")
        return {"error": str(e)}

async def refine_speech_to_text(text: str, level: str, question: dict):
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = await get_system_prompt(level)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt+"\n입력부분에 풀이 방식이 들어가니까 그 부분을 반영한 답을 적어줘"},
                {"role": "user", "content": f"문제: {question['question']}\n내용: {question['content']}\n보기: {', '.join(question['choices'])}"},
                {"role": "user", "content": f"음성 인식 결과: {text}"},
                {"role": "user", "content": "위의 음성 인식 결과는 문제의 풀이야. 시스템 프롬프트에 맞게 정제해서 풀이를 작성해줘."},
            ],
        )
        
        refined_text = response.choices[0].message.content
        return refined_text
    except Exception as e:
        print(f"Error refining speech to text: {str(e)}")
        return text
