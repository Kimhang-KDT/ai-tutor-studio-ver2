// Questions 컴포넌트: 모든 테스트의 목록을 표시하고 관리하는 컴포넌트

import React, { useState, useEffect } from 'react';
import { Box, Button, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { getTestInfos } from '../services/api';

// TestInfo 인터페이스: 각 테스트의 정보를 정의
interface TestInfo {
  testId: string;
  subjectId: string;
  test_month: string;
  subject_name: string;
  is_ready: boolean;
}

const Questions: React.FC = () => {
  // 상태 관리: 테스트 정보 목록
  const [testInfos, setTestInfos] = useState<TestInfo[]>([]);
  const navigate = useNavigate();

  // 컴포넌트 마운트 시 테스트 정보 로드
  useEffect(() => {
    const fetchTestInfos = async () => {
      const data = await getTestInfos();
      setTestInfos(data);
    };
    fetchTestInfos();
  }, []);

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>모의고사</TableCell>
            <TableCell>과목</TableCell>
            <TableCell>데이터 상태</TableCell>
            <TableCell>풀이</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {/* 테스트 정보 목록을 순회하며 각 행 렌더링 */}
          {testInfos.map((testInfo, index) => (
            <TableRow key={index}>
              <TableCell>{testInfo.test_month}</TableCell>
              <TableCell>{testInfo.subject_name}</TableCell>
              <TableCell>
                {/* 데이터 상태에 따른 시각적 표시 */}
                <Box
                  component="span"
                  sx={{
                    backgroundColor: testInfo.is_ready ? '#90EE90' : '#FFA500',
                    padding: '5px 10px',
                    borderRadius: '4px',
                    color: 'white',
                  }}
                >
                  {testInfo.is_ready ? '완료' : '미완'}
                </Box>
              </TableCell>
              <TableCell>
                {/* 수정 버튼: 클릭 시 해당 테스트의 상세 페이지로 이동 */}
                <Button
                  variant="contained"
                  onClick={() => navigate(`/questions/${testInfo.testId}/${testInfo.subjectId}`)}
                >
                  수정
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default Questions;
