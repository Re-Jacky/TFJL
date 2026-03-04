import React, { useEffect, useRef, useState } from 'react';
import { Select, Button, message, Space, Tag, Modal } from 'antd';
import styles from './ScriptEditorContent.module.scss';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  SaveOutlined,
  CheckCircleOutlined,
  BugOutlined,
} from '@ant-design/icons';
import { api } from '@src/services/api';
import CodeEditor, {
  type EditorHandler,
} from '@src/components/editor/CodeEditor';
import CreateFileButton from '../components/CreateFileButton';
import DeleteFileButton from '../components/DeleteFileButton';
import { useSelector } from 'react-redux';
import {
  selectActiveWindow,
  selectInitializing,
  selectSseSessionId,
} from '@src/store/selectors';
import type {
  ScriptExecutionStatus,
  ScriptExecutionRequest,
  ParseScriptResponse,
  ValidateScriptResponse,
  TestScriptResponse,
} from '@src/types';

type ScriptType = 'collab' | 'activity';

interface FileOption {
  value: string;
  label: string;
}

export const ScriptEditorContent: React.FC = () => {
  const [scriptType, setScriptType] = useState<ScriptType>('collab');
  const [selectedFile, setSelectedFile] = useState<string>();
  const [fileOptions, setFileOptions] = useState<Array<FileOption>>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [initialContent, setInitialContent] = useState('');
  const [status, setStatus] = useState<ScriptExecutionStatus | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
  const [testModalVisible, setTestModalVisible] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{
    parse?: ParseScriptResponse;
    validate?: ValidateScriptResponse;
  } | null>(null);
  const [testing, setTesting] = useState<boolean>(false);
  const [execTestModalVisible, setExecTestModalVisible] =
    useState<boolean>(false);
  const [execTestResult, setExecTestResult] =
    useState<TestScriptResponse | null>(null);
  const [execTesting, setExecTesting] = useState<boolean>(false);
  const [dryRunning, setDryRunning] = useState<boolean>(false);

  const editorRef = useRef<EditorHandler | null>(null);
  const activeWindow = useSelector(selectActiveWindow);
  const sseSessionId = useSelector(selectSseSessionId);
  const initializing = useSelector(selectInitializing);
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const loadFiles = async (type: ScriptType) => {
    setLoading(true);
    try {
      const data = await api.getFileList(type);
      const options = data.files.map((item) => ({
        value: item,
        label: item,
      }));
      setFileOptions(options);

      // If currently selected file is not in list, clear selection or select first
      if (selectedFile && !data.files.includes(selectedFile)) {
        setSelectedFile(options.length > 0 ? options[0].value : undefined);
      } else if (!selectedFile && options.length > 0) {
        setSelectedFile(options[0].value);
      }
    } catch (error) {
      console.error(error);
      message.error('Failed to load file list');
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (file: string, type: ScriptType) => {
    try {
      const content = await api.readFile(file, type);
      setInitialContent(content);
      if (editorRef.current) {
        // We can't set content directly on ref if it doesn't expose setContent
        // But the CodeEditor likely takes `content` prop or similar
        // Looking at CollaborationContent, it uses `initContent` prop on CodeEditor
      }
    } catch (error) {
      console.error(error);
      message.error('Failed to load file content');
    }
  };

  // Initial load
  useEffect(() => {
    if (!initializing) {
      loadFiles(scriptType);
    }
  }, [initializing, scriptType]);

  // Load content when file selection changes
  useEffect(() => {
    if (selectedFile) {
      loadFileContent(selectedFile, scriptType);
    } else {
      setInitialContent('');
    }
  }, [selectedFile, scriptType]);

  // Polling for status
  useEffect(() => {
    const pollStatus = async () => {
      if (!activeWindow) return;
      try {
        const res = await api.getScriptStatus(parseInt(activeWindow));
        if (res.success) {
          setStatus(res.status);

          // Stop polling if stopped or error, unless we want to keep checking
          if (res.status.state === 'stopped' || res.status.state === 'error') {
            // Keep polling? Maybe not.
            // But user might restart from outside. Better keep polling if we started it.
          }
        }
      } catch (error) {
        console.error('Status poll failed', error);
      }
    };

    if (polling && activeWindow) {
      pollingTimerRef.current = setInterval(pollStatus, 1000);
      pollStatus(); // immediate check
    } else {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    }

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
      }
    };
  }, [polling, activeWindow]);

  // Start polling when component mounts if active window exists
  useEffect(() => {
    if (activeWindow) {
      setPolling(true);
    }
    return () => setPolling(false);
  }, [activeWindow]);

  const handleCreateFile = async (fileName: string) => {
    const file = `${fileName}.txt`;
    try {
      await api.saveFile(file, '', scriptType);
      await loadFiles(scriptType);
      setSelectedFile(file);
      message.success('File created');
    } catch (error) {
      console.error(error);
      message.error('Failed to create file');
    }
  };

  const handleDeleteFile = async () => {
    if (!selectedFile) return;
    try {
      await api.deleteFile(selectedFile, scriptType);
      await loadFiles(scriptType);
      message.success('File deleted');
    } catch (error) {
      console.error(error);
      message.error('Failed to delete file');
    }
  };

  const handleSave = async () => {
    if (!selectedFile) return;
    const content = editorRef.current?.getContent() || '';
    try {
      await api.saveFile(selectedFile, content, scriptType);
      message.success('File saved');
    } catch (error) {
      console.error(error);
      message.error('Failed to save file');
    }
  };

  const handleTest = async () => {
    const content = editorRef.current?.getContent() || '';
    if (!content.trim()) {
      message.warning('Please enter script content to test');
      return;
    }

    setTesting(true);
    try {
      const [parseRes, validateRes] = await Promise.all([
        api.parseScript(content, selectedFile || 'test.txt', scriptType),
        api.validateScript(content),
      ]);
      setTestResult({ parse: parseRes, validate: validateRes });
      setTestModalVisible(true);
    } catch (error) {
      console.error(error);
      message.error('Failed to test script');
    } finally {
      setTesting(false);
    }
  };

  const handleTestExecution = async () => {
    const content = editorRef.current?.getContent() || '';
    if (!content.trim()) {
      message.warning('Please enter script content to test');
      return;
    }

    setExecTesting(true);
    try {
      const result = await api.testScript(
        content,
        selectedFile || 'test.txt',
        scriptType
      );
      setExecTestResult(result);
      setExecTestModalVisible(true);
    } catch (error) {
      console.error(error);
      message.error('Failed to test script execution');
    } finally {
      setExecTesting(false);
    }
  };

  const handleDryRun = async () => {
    const content = editorRef.current?.getContent() || '';
    if (!content.trim()) {
      message.warning('Please enter script content to test');
      return;
    }

    if (!sseSessionId) {
      message.warning('SSE not connected. Please wait for connection.');
      return;
    }

    setDryRunning(true);
    try {
      // Use actual SSE session ID to ensure events reach the connected client
      const result = await api.testScript(
        content,
        selectedFile || 'test.txt',
        scriptType,
        {
          dryRun: true,
          sessionId: sseSessionId,
          actionDelayMs: 300,
          levelDelayMs: 500,
        }
      );
      setExecTestResult(result);
      setExecTestModalVisible(true);
    } catch (error) {
      console.error(error);
      message.error('Dry run failed');
    } finally {
      setDryRunning(false);
    }
  };

  const executeAction = async (
    action: 'start' | 'pause' | 'resume' | 'stop'
  ) => {
    if (!selectedFile || !activeWindow) {
      message.warning(
        'Please select a file and ensure a game window is active'
      );
      return;
    }

    const request: ScriptExecutionRequest = {
      script_name: selectedFile,
      script_type: scriptType,
      window_pid: parseInt(activeWindow),
      action: action,
    };

    try {
      const res = await api.executeScript(request);
      if (res.success) {
        message.success(`Action ${action} successful`);
        setPolling(true);
        // Refresh status immediately
        const statusRes = await api.getScriptStatus(parseInt(activeWindow));
        if (statusRes.success) setStatus(statusRes.status);
      } else {
        message.error(`Action failed: ${res.message}`);
      }
    } catch (error) {
      console.error(error);
      message.error(`Failed to execute ${action}`);
    }
  };

  const renderStatus = () => {
    if (!status) return null;

    let color = 'default';
    if (status.state === 'running') color = 'green';
    if (status.state === 'paused') color = 'gold';
    if (status.state === 'stopped') color = 'default';
    if (status.state === 'error') color = 'red';

    return (
      <div className={`${styles.status} ${styles[status.state]}`}>
        <Space wrap>
          <Tag color={color}>{status.state.toUpperCase()}</Tag>
          <span>Level: {status.current_level}</span>
          <span>Time: {status.current_second}s</span>
          <span>Actions: {status.actions_executed}</span>
          {status.error_message && (
            <span style={{ color: 'red' }}>Error: {status.error_message}</span>
          )}
        </Space>
      </div>
    );
  };

  const validateDuplicateFiles = (name: string) => {
    const file = `${name}.txt`;
    return !fileOptions.some((option) => option.value === file);
  };

  return (
    <div className={styles.scriptEditor}>
      <div className={styles.header}>
        <div className={styles.leftParams}>
          <Select
            value={scriptType}
            onChange={(value) => setScriptType(value)}
            options={[
              { value: 'collab', label: 'Collaboration' },
              { value: 'activity', label: 'Activity' },
            ]}
            style={{ width: 120 }}
          />

          <div className={styles.select}>
            <span>File:</span>
            <Select
              style={{ width: 200 }}
              value={selectedFile}
              onChange={setSelectedFile}
              options={fileOptions}
              loading={loading}
              placeholder='Select a script'
            />
          </div>

          <CreateFileButton
            onSave={handleCreateFile}
            validator={validateDuplicateFiles}
          />

          <DeleteFileButton
            onDelete={handleDeleteFile}
            disabled={!selectedFile}
          />
        </div>

        <div className={styles.btnGroup}>
          <Button
            icon={<CheckCircleOutlined />}
            onClick={handleTest}
            loading={testing}
          >
            Validate
          </Button>
          <Button
            icon={<BugOutlined />}
            onClick={handleTestExecution}
            loading={execTesting}
          >
            Test
          </Button>
          <Button
            icon={<BugOutlined />}
            onClick={handleDryRun}
            loading={dryRunning}
            type='dashed'
          >
            Dry Run
          </Button>
          <Button
            type='primary'
            icon={<SaveOutlined />}
            onClick={handleSave}
            disabled={!selectedFile}
          >
            Save
          </Button>
          <Button
            type='primary'
            icon={<PlayCircleOutlined />}
            onClick={() => executeAction('start')}
            disabled={
              !selectedFile || !activeWindow || status?.state === 'running'
            }
            style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
          >
            Start
          </Button>
          <Button
            icon={<PauseCircleOutlined />}
            onClick={() => executeAction('pause')}
            disabled={!activeWindow || status?.state !== 'running'}
          >
            Pause
          </Button>
          <Button
            icon={<PlayCircleOutlined />}
            onClick={() => executeAction('resume')}
            disabled={!activeWindow || status?.state !== 'paused'}
          >
            Resume
          </Button>
          <Button
            danger
            icon={<StopOutlined />}
            onClick={() => executeAction('stop')}
            disabled={
              !activeWindow ||
              (status?.state !== 'running' && status?.state !== 'paused')
            }
          >
            Stop
          </Button>
        </div>
      </div>

      {activeWindow && renderStatus()}

      <div className={styles.scriptSection}>
        <CodeEditor
          ref={editorRef}
          value={initialContent}
          height={230}
          onChange={() => {}}
        />
      </div>

      <Modal
        title='Script Validation Results'
        open={testModalVisible}
        onCancel={() => setTestModalVisible(false)}
        footer={[
          <Button key='close' onClick={() => setTestModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={600}
      >
        {testResult && (
          <div>
            <h4>Parse Result</h4>
            <p>
              Status:{' '}
              <Tag color={testResult.parse?.success ? 'green' : 'red'}>
                {testResult.parse?.success ? 'SUCCESS' : 'FAILED'}
              </Tag>
            </p>
            {testResult.parse?.errors && testResult.parse.errors.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <strong>Errors:</strong>
                <ul style={{ color: 'red', margin: '4px 0' }}>
                  {testResult.parse.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
            {testResult.parse?.warnings &&
              testResult.parse.warnings.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <strong>Warnings:</strong>
                  <ul style={{ color: 'orange', margin: '4px 0' }}>
                    {testResult.parse.warnings.map((warn, i) => (
                      <li key={i}>{warn}</li>
                    ))}
                  </ul>
                </div>
              )}

            <h4 style={{ marginTop: 16 }}>Validation Result</h4>
            <p>
              Status:{' '}
              <Tag color={testResult.validate?.valid ? 'green' : 'red'}>
                {testResult.validate?.valid ? 'VALID' : 'INVALID'}
              </Tag>
            </p>
            {testResult.validate?.errors &&
              testResult.validate.errors.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <strong>Errors:</strong>
                  <ul style={{ color: 'red', margin: '4px 0' }}>
                    {testResult.validate.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            {testResult.validate?.warnings &&
              testResult.validate.warnings.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <strong>Warnings:</strong>
                  <ul style={{ color: 'orange', margin: '4px 0' }}>
                    {testResult.validate.warnings.map((warn, i) => (
                      <li key={i}>{warn}</li>
                    ))}
                  </ul>
                </div>
              )}

            {testResult.parse?.success && testResult.parse?.script && (
              <div style={{ marginTop: 16 }}>
                <h4>Parsed Script Structure</h4>
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    maxHeight: 300,
                    overflow: 'auto',
                    fontSize: 12,
                  }}
                >
                  {JSON.stringify(testResult.parse.script, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal
        title='Script Test Execution Results'
        open={execTestModalVisible}
        onCancel={() => setExecTestModalVisible(false)}
        footer={[
          <Button key='close' onClick={() => setExecTestModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {execTestResult && (
          <div>
            <p>
              Status:{' '}
              <Tag color={execTestResult.success ? 'green' : 'red'}>
                {execTestResult.success ? 'SUCCESS' : 'FAILED'}
              </Tag>
            </p>

            {execTestResult.errors.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <strong>Errors:</strong>
                <ul style={{ color: 'red', margin: '4px 0' }}>
                  {execTestResult.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {execTestResult.warnings.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <strong>Warnings:</strong>
                <ul style={{ color: 'orange', margin: '4px 0' }}>
                  {execTestResult.warnings.map((warn, i) => (
                    <li key={i}>{warn}</li>
                  ))}
                </ul>
              </div>
            )}

            {execTestResult.summary && (
              <div style={{ marginBottom: 16 }}>
                <h4>Summary</h4>
                <Space wrap>
                  <Tag>
                    Total Actions: {execTestResult.summary.total_actions}
                  </Tag>
                  <Tag>Levels: {execTestResult.summary.level_count}</Tag>
                  <Tag>Events: {execTestResult.summary.event_count}</Tag>
                </Space>
                <div style={{ marginTop: 8 }}>
                  <strong>Cards Used:</strong>{' '}
                  {execTestResult.summary.cards_used.join(', ') || 'None'}
                </div>
                <div style={{ marginTop: 4 }}>
                  <strong>Deck:</strong>{' '}
                  {execTestResult.summary.deck.join(', ') || 'Not specified'}
                </div>
              </div>
            )}

            {execTestResult.action_log.length > 0 && (
              <div>
                <h4>Action Log ({execTestResult.action_log.length} actions)</h4>
                <div
                  style={{
                    maxHeight: 400,
                    overflow: 'auto',
                    border: '1px solid #d9d9d9',
                    borderRadius: 4,
                  }}
                >
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: 12,
                    }}
                  >
                    <thead>
                      <tr
                        style={{
                          background: '#fafafa',
                          position: 'sticky',
                          top: 0,
                        }}
                      >
                        <th
                          style={{
                            padding: '8px',
                            borderBottom: '1px solid #d9d9d9',
                            textAlign: 'left',
                          }}
                        >
                          Level
                        </th>
                        <th
                          style={{
                            padding: '8px',
                            borderBottom: '1px solid #d9d9d9',
                            textAlign: 'left',
                          }}
                        >
                          Second
                        </th>
                        <th
                          style={{
                            padding: '8px',
                            borderBottom: '1px solid #d9d9d9',
                            textAlign: 'left',
                          }}
                        >
                          Type
                        </th>
                        <th
                          style={{
                            padding: '8px',
                            borderBottom: '1px solid #d9d9d9',
                            textAlign: 'left',
                          }}
                        >
                          Description
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {execTestResult.action_log.map((action, i) => (
                        <tr
                          key={i}
                          style={{ borderBottom: '1px solid #f0f0f0' }}
                        >
                          <td style={{ padding: '6px 8px' }}>
                            {action.level || '-'}
                          </td>
                          <td style={{ padding: '6px 8px' }}>
                            {action.second ?? '-'}
                          </td>
                          <td style={{ padding: '6px 8px' }}>
                            <Tag>{action.action_type}</Tag>
                          </td>
                          <td style={{ padding: '6px 8px' }}>
                            {action.description}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ScriptEditorContent;
