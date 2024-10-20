// Tests 컴포넌트: 모든 테스트와 관련 모델의 상태를 표시하고 관리하는 메인 컴포넌트

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { TableContainer, Table, TableHead, TableRow, TableCell, TableBody, Paper, Typography, Button, CircularProgress } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { getDatalists, createFinetuningModel, getFinetuningStatus, createFinetunedAnswers } from '../services/api';

interface ModelInfo {
  fine_tuned_model: string | null;
  status: 'idle' | 'creating' | 'pending' | 'running' | 'succeeded' | 'failed' | 'validating_files';
  job_id: string | null;
  answers_status: 'idle' | 'creating' | 'completed';
}

interface TestsInfo {
  testId: string;
  subjectId: string;
  test_month: string;
  subject_name: string;
  is_ready: boolean;
  levels: {
    base: ModelInfo | null;
    low: ModelInfo | null;
    medium: ModelInfo | null;
    high: ModelInfo | null;
  };
}

interface ModelStatus {
  [key: string]: {
    status: 'idle' | 'creating' | 'pending' | 'running' | 'succeeded' | 'failed' | 'validating_files';
    progress?: number;
    answers_status: 'idle' | 'creating' | 'completed' | 'failed';
  };
}

const Tests: React.FC = () => {
  // 상태 관리
  const [testsInfo, setTestsInfo] = useState<TestsInfo[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatus>({});
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const activeJobsRef = useRef<Set<string>>(new Set());

  // 테스트 정보 가져오기
  const fetchTestsInfo = useCallback(async () => {
    try {
      const data: TestsInfo[] = await getDatalists();
      setTestsInfo(data);
      initializeModelStatus(data);
      
      // 진행 중인 모델에 대해 상태 확인 시작
      data.forEach((testInfo: TestsInfo) => {
        Object.entries(testInfo.levels).forEach(([level, modelInfo]) => {
          if (modelInfo && modelInfo.job_id && (modelInfo.status === 'running' || modelInfo.status === 'pending' || modelInfo.status === 'validating_files')) {
            activeJobsRef.current.add(modelInfo.job_id);
            checkModelStatus(modelInfo.job_id, testInfo.testId, testInfo.subjectId, level);
          }
        });
      });
    } catch (err) {
      console.error('Error fetching tests info:', err);
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
    }
  }, []);

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    fetchTestsInfo();
  }, [fetchTestsInfo]);

  // 주기적으로 활성 작업 상태 확인
  useEffect(() => {
    const intervalId = setInterval(() => {
      if (activeJobsRef.current.size > 0) {
        fetchTestsInfo();
      }
    }, 30000);
    return () => clearInterval(intervalId);
  }, [fetchTestsInfo]);

  // 모델 상태 초기화
  const initializeModelStatus = (data: TestsInfo[]) => {
    const initialStatus: ModelStatus = {};
    data.forEach(testInfo => {
      Object.entries(testInfo.levels).forEach(([level, modelInfo]) => {
        const key = `${testInfo.testId}-${testInfo.subjectId}-${level}`;
        if (modelInfo) {
          initialStatus[key] = { 
            status: modelInfo.status,
            progress: modelInfo.status === 'succeeded' ? 100 : (modelInfo.status === 'running' ? 50 : 0),
            answers_status: modelInfo.answers_status
          };
        } else {
          initialStatus[key] = { status: 'idle', progress: 0, answers_status: 'idle' };
        }
      });
    });
    setModelStatus(initialStatus);
  };

  // 새 모델 생성 처리
  const handleCreateModel = async (testId: string, subjectId: string, level: string) => {
    const statusKey = `${testId}-${subjectId}-${level}`;
    try {
      setModelStatus(prev => ({
        ...prev,
        [statusKey]: { status: 'creating', progress: 0, answers_status: 'idle' }
      }));
      const result = await createFinetuningModel(testId, subjectId, level);
      if (result.error) {
        throw new Error(result.error);
      }
      setModelStatus(prev => ({
        ...prev,
        [statusKey]: { status: 'pending', progress: 0, answers_status: 'idle' }
      }));
      activeJobsRef.current.add(result.job_id);
      await checkModelStatus(result.job_id, testId, subjectId, level);
    } catch (err) {
      console.error('Error creating finetuning model:', err);
      setError(`파인튜닝 모델 생성 중 오류가 발생했습니다: ${(err as Error).message}`);
      setModelStatus(prev => ({
        ...prev,
        [statusKey]: { status: 'failed', progress: 0, answers_status: 'idle' }
      }));
    }
  };

  // 모델 상태 확인
  const checkModelStatus = useCallback(async (jobId: string | null, testId: string, subjectId: string, level: string) => {
    if (!jobId) {
      console.error('Job ID is null or undefined');
      return;
    }

    const statusKey = `${testId}-${subjectId}-${level}`;
    try {
      const status = await getFinetuningStatus(jobId);
      if (status.error) {
        throw new Error(status.error);
      }
      setModelStatus(prev => ({
        ...prev,
        [statusKey]: { 
          status: status.status as ModelStatus[string]['status'],
          progress: status.status === 'succeeded' ? 100 : (status.status === 'running' ? 50 : 0),
          answers_status: prev[statusKey]?.answers_status || 'idle'
        }
      }));
      if (status.status !== 'succeeded' && status.status !== 'failed' && status.status !== 'cancelled') {
        setTimeout(() => checkModelStatus(jobId, testId, subjectId, level), 10000);
      } else {
        activeJobsRef.current.delete(jobId);
        await fetchTestsInfo();
      }
    } catch (err) {
      console.error('Error checking model status:', err);
      setModelStatus(prev => ({
        ...prev,
        [statusKey]: { status: 'failed', progress: 0, answers_status: 'idle' }
      }));
      activeJobsRef.current.delete(jobId);
    }
  }, [fetchTestsInfo]);

  // 파인튜닝된 답변 생성
  const handleCreateAnswers = async (testId: string, subjectId: string, level: string, modelId: string) => {
    const statusKey = `${testId}-${subjectId}-${level}`;
    try {
      setModelStatus(prev => ({
        ...prev,
        [statusKey]: { ...prev[statusKey], answers_status: 'creating' }
      }));
      const result = await createFinetunedAnswers(modelId, level, testId, subjectId);
      if (result.error) {
        throw new Error(result.error);
      }
      setModelStatus(prev => ({
        ...prev,
        [statusKey]: { ...prev[statusKey], answers_status: 'completed' }
      }));
      await fetchTestsInfo();
    } catch (err) {
      console.error('Error creating finetuned answers:', err);
      setError(`파인튜닝된 답변 생성 중 오류가 발생했습니다: ${(err as Error).message}`);
      setModelStatus(prev => ({
        ...prev,
        [statusKey]: { ...prev[statusKey], answers_status: 'failed' }
      }));
    }
  };

  // 모델 상태 렌더링
  const renderStatus = (status: ModelStatus[string]) => {
    switch (status.status) {
      case 'idle':
        return '-';
      case 'creating':
        return '생성 중...';
      case 'pending':
        return '대기 중...';
      case 'running':
        return (
          <div>
            진행 중 <CircularProgress size={20} />
          </div>
        );
      case 'succeeded':
        return '완료';
      case 'failed':
        return '실패';
      case 'validating_files':
        return '파일 검증 중...';
      default:
        return '-';
    }
  };

  // 테스트 페이지로 이동
  const handleTestClick = (testId: string, subjectId: string, level: string) => {
    navigate(`/tests/${testId}/${subjectId}/${level}`);
  };

  // 에러 처리
  if (error) {
    return <Typography color="error">{error}</Typography>;
  }

  // 테이블 렌더링
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>모의고사</TableCell>
            <TableCell>과목</TableCell>
            <TableCell>데이터 상태</TableCell>
            <TableCell>풀이 레벨</TableCell>
            <TableCell>액션</TableCell>
            <TableCell>진행 상태</TableCell>
            <TableCell>답변 생성</TableCell>
            <TableCell>답변 상태</TableCell>
            <TableCell>테스트</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {testsInfo.flatMap((testInfo, index) => 
            Object.entries(testInfo.levels)
              .filter(([level, _]) => level !== 'base') // base 레벨 제외
              .map(([level, model]) => {
                const statusKey = `${testInfo.testId}-${testInfo.subjectId}-${level}`;
                const status = modelStatus[statusKey] || { status: 'idle', answers_status: 'idle' };
                const isModelComplete = status.status === 'succeeded' || status.status === 'failed';
                const buttonText = model ? '모델 업데이트' : '모델 생성';
                const answerButtonText = status.answers_status === 'completed' ? '답변 업데이트' : '답변 생성';
                return (
                  <TableRow key={`${index}-${level}`}>
                    <TableCell>{testInfo.test_month}</TableCell>
                    <TableCell>{testInfo.subject_name}</TableCell>
                    <TableCell>{testInfo.is_ready ? '완료' : '미완료'}</TableCell>
                    <TableCell>{level.toUpperCase()}</TableCell>
                    <TableCell>
                      <Button
                        variant="contained"
                        disabled={!testInfo.is_ready || (!isModelComplete && status.status !== 'idle')}
                        onClick={() => handleCreateModel(testInfo.testId, testInfo.subjectId, level)}
                      >
                        {buttonText}
                      </Button>
                    </TableCell>
                    <TableCell>{renderStatus(status)}</TableCell>
                    <TableCell>
                      <Button
                        variant="contained"
                        disabled={!isModelComplete || status.answers_status === 'creating'}
                        onClick={() => handleCreateAnswers(testInfo.testId, testInfo.subjectId, level, model?.fine_tuned_model || '')}
                      >
                        {answerButtonText}
                      </Button>
                    </TableCell>
                    <TableCell>{status.answers_status === 'completed' ? '완료' : status.answers_status}</TableCell>
                    <TableCell>
                      <Button
                        variant="contained"
                        disabled={!isModelComplete}
                        onClick={() => handleTestClick(testInfo.testId, testInfo.subjectId, level)}
                      >
                        테스트
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default Tests;
