from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from datetime import datetime
from bson import ObjectId
import json

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

client = AsyncIOMotorClient(f"{settings.DATABASE_URL}&tls=true")
db = client[settings.MONGODB_DB_NAME]

async def init_db():
    try:
        await client.admin.command('ping')
        print("데이터베이스에 성공적으로 연결되었습니다.")
        print(f"연결된 데이터베이스: {settings.MONGODB_DB_NAME}")
    except Exception as e:
        print(f"데이터베이스 연결 실패: {str(e)}")
        print(f"시도한 연결 URL: {settings.DATABASE_URL}")
        raise

async def get_collection(collection_name: str):
    return db[collection_name]

async def get_test_infos():
    collection = await get_collection("test_info")
    cursor = collection.find({}, {"_id": 0, "testId": 1, "subjectId": 1, "test_month": 1, "subject_name": 1, "is_ready": 1})
    test_infos = await cursor.to_list(length=None)
    return json.loads(json.dumps(test_infos, cls=JSONEncoder))

async def get_questions():
    collection = await get_collection("questions")
    cursor = collection.find({}, {"_id": 0, "testId": 1, "subjectId": 1, "test_month": 1, "subject_name": 1})
    questions = await cursor.to_list(length=None)
    return json.loads(json.dumps(questions, cls=JSONEncoder))

async def get_questions_by_info(testId: str, subjectId: str):
    collection = await get_collection("questions")
    cursor = collection.find(
        {"testId": int(testId), "subjectId": int(subjectId)},
        {"_id": 0, "testId": 1, "subjectId": 1, "question_number": 1, "question": 1, "content": 1, "choices": 1, "test_month": 1, "subject_name": 1}
    )
    questions = await cursor.to_list(length=None)
    print(questions)
    return json.loads(json.dumps(questions, cls=JSONEncoder))

async def get_answers(testId: str, subjectId: str, collection_name: str):
    collection = await get_collection(collection_name)
    cursor = collection.find({"testId": int(testId), "subjectId": int(subjectId)})
    answers = await cursor.to_list(length=None)
    return json.loads(json.dumps(answers, cls=JSONEncoder))

async def save_answer(test_id: str, subject_id: str, answer_data: dict, collection_name: str, update=False):
    collection = await get_collection(collection_name)
    
    document = {
        "test_month": answer_data['test_month'],
        "subject_name": answer_data['subject_name'],
        "question_num": answer_data['question_num'],
        "answer": answer_data['answer'],
        "testId": int(test_id),
        "subjectId": int(subject_id)
    }
    
    if update:
        result = await collection.update_one(
            {"testId": int(test_id), "subjectId": int(subject_id), "question_num": answer_data['question_num']},
            {"$set": document}
        )
    else:
        result = await collection.insert_one(document)
    
    return str(result.inserted_id) if not update else "Updated successfully"

async def get_answer_collection(collection_name: str):
    return await get_collection(collection_name)

async def check_answer_exists(test_id: str, subject_id: str, question_num: str, collection_name: str):
    collection = await get_collection(collection_name)
    existing_answer = await collection.find_one({
        "testId": int(test_id),
        "subjectId": int(subject_id),
        "question_num": question_num
    })
    return existing_answer is not None

async def update_test_info_ready_status(test_id: str, subject_id: str, is_ready: bool):
    collection = await get_collection("test_info")
    await collection.update_one(
        {"testId": int(test_id), "subjectId": int(subject_id)},
        {"$set": {"is_ready": is_ready}}
    )

async def db_get_datalists():
    test_info_collection = await get_collection("test_info")
    llm_models_collection = await get_collection("llm_models")
    
    cursor = test_info_collection.find({}, {"_id": 0, "testId": 1, "subjectId": 1, "test_month": 1, "subject_name": 1, "is_ready": 1})
    test_infos = await cursor.to_list(length=None)
    
    result = []
    for test_info in test_infos:
        test_info['levels'] = {}
        for level in ['low', 'medium', 'high']:
            model = await llm_models_collection.find_one(
                {"testId": test_info['testId'], "subjectId": test_info['subjectId'], "level": level},
                {"_id": 0, "fine_tuned_model": 1, "status": 1, "job_id": 1}
            )
            answers_status = await check_level_answers_status(test_info['testId'], test_info['subjectId'], level)
            if model:
                test_info['levels'][level] = {
                    "fine_tuned_model": model['fine_tuned_model'],
                    "status": model['status'],
                    "job_id": model['job_id'],
                    "answers_status": answers_status
                }
            else:
                test_info['levels'][level] = None
        result.append(test_info)
    
    return json.loads(json.dumps(result, cls=JSONEncoder))

async def check_level_answers_status(test_id: str, subject_id: str, level: str):
    level_answers_collection = await get_collection("level_answers")
    count = await level_answers_collection.count_documents({
        "testId": int(test_id),
        "subjectId": int(subject_id),
        "level": level
    })
    
    if count == 0:
        return 'idle'
    elif count < await get_total_questions_count(test_id, subject_id):
        return 'creating'
    else:
        return 'completed'

async def get_total_questions_count(test_id: str, subject_id: str):
    questions_collection = await get_collection("questions")
    return await questions_collection.count_documents({
        "testId": int(test_id),
        "subjectId": int(subject_id)
    })

# 기존 코드에 다음 함수를 추가합니다.

async def save_llm_model(test_id: str, subject_id: str, level: str, status: str, fine_tuned_model: str, job_id: str):
    collection = await get_collection("llm_models")
    document = {
        "testId": int(test_id),
        "subjectId": int(subject_id),
        "level": level,
        "status": status,
        "fine_tuned_model": fine_tuned_model,
        "job_id": job_id
    }
    await collection.update_one(
        {"testId": int(test_id), "subjectId": int(subject_id), "level": level},
        {"$set": document},
        upsert=True
    )

async def update_llm_model_status(job_id: str, status: str, fine_tuned_model: str = None):
    collection = await get_collection("llm_models")
    update_data = {"status": status}
    if fine_tuned_model:
        update_data["fine_tuned_model"] = fine_tuned_model
    await collection.update_one(
        {"job_id": job_id},
        {"$set": update_data}
    )

async def get_system_prompt(level: str):
    collection = await get_collection("prompts")
    prompt = await collection.find_one({"level": level})
    return prompt["system_prompt"]

async def save_level_answer(test_id: str, subject_id: str, level: str, answer_data: dict):
    collection = await get_collection("level_answers")
    document = {
        "testId": int(test_id),
        "subjectId": int(subject_id),
        "level": level,
        "question_num": answer_data["question_num"],
        "answer": answer_data["answer"],
        "test_month": answer_data["test_month"],
        "subject_name": answer_data["subject_name"]
    }
    await collection.update_one(
        {"testId": int(test_id), "subjectId": int(subject_id), "level": level, "question_num": answer_data["question_num"]},
        {"$set": document},
        upsert=True
    )

async def get_level_answers(test_id: str, subject_id: str, level: str):
    collection = await get_collection("level_answers")
    cursor = collection.find({
        "testId": int(test_id),
        "subjectId": int(subject_id),
        "level": level
    })
    answers = await cursor.to_list(length=None)
    return json.loads(json.dumps(answers, cls=JSONEncoder))
