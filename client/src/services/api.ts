import axios from "axios";

const API_BASE_URL = "http://130.162.154.159:8001";

export const getTestInfos = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/test_infos`);
    return response.data;
  } catch (error) {
    console.error("Error fetching test infos:", error);
    throw error;
  }
};

export const getQuestions = async (testId: string, subjectId: string) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/questions/${testId}/${subjectId}`
    );
    return response.data;
  } catch (error) {
    console.error("Error fetching questions:", error);
    throw error;
  }
};

export const saveAnswer = async (
  testId: string,
  subjectId: string,
  questionNum: string,
  answerType: string,
  answer: string,
  testMonth: string,
  subjectName: string
) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/answer/${testId}/${subjectId}`,
      {
        question_num: questionNum,
        answer_type: answerType,
        answer: answer,
        test_month: testMonth,
        subject_name: subjectName,
      }
    );
    return response.data;
  } catch (error) {
    console.error("답변 저장 중 오류 발생:", error);
    throw error;
  }
};

export const getAnswerStatus = async (testId: string, subjectId: string) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/answer_status/${testId}/${subjectId}`
    );
    return response.data;
  } catch (error) {
    console.error("답변 상태 가져오기 중 오류 발생:", error);
    throw error;
  }
};

export const getSpecificAnswer = async (
  testId: string,
  subjectId: string,
  questionNum: string,
  answerType: string
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/answer/${testId}/${subjectId}/${questionNum}/${answerType}`
    );
    return response.data.answer;
  } catch (error) {
    console.error("특정 답변 가져오기 중 오류 발생:", error);
    return "";
  }
};

export const createFinetuningModel = async (
  testId: string,
  subjectId: string,
  level: string
) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/finetuning/${testId}/${subjectId}/${level}`
    );
    return response.data;
  } catch (error) {
    console.error("Finetuning 모델 생성 중 오류 발생:", error);
    throw error;
  }
};

export const getDatalists = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/finetuning/datalists`);
    return response.data;
  } catch (error) {
    console.error("Finetuning 데이터셋 가져오기 중 오류 발생:", error);
    throw error;
  }
};

export const getFinetuningStatus = async (jobId: string) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/finetuning_status/${jobId}`
    );
    return response.data;
  } catch (error) {
    console.error("Finetuning 상태 확인 중 오류 발생:", error);
    throw error;
  }
};

export const testFinetunedAnswers = async (
  testId: string,
  subjectId: string,
  level: string
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/finetuned_answers/${testId}/${subjectId}/${level}`
    );
    return response.data;
  } catch (error) {
    console.error("Finetuned 답변 테스트 중 오류 발생:", error);
    throw error;
  }
};

export const convertSpeechToText = async (audioBlob: Blob): Promise<string> => {
  try {
    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.wav");

    const response = await axios.post(
      `${API_BASE_URL}/speech-to-text`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    return response.data.text;
  } catch (error) {
    console.error("음성을 텍스트로 변환하는 중 오류 발생:", error);
    throw error;
  }
};

export const createFinetunedAnswers = async (
  modelId: string,
  level: string,
  testId: string,
  subjectId: string
) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/finetuned_answers/${modelId}/${level}/${testId}/${subjectId}`
    );
    return response.data;
  } catch (error) {
    console.error("Finetuned 답변 생성 중 오류 발생:", error);
    throw error;
  }
};
