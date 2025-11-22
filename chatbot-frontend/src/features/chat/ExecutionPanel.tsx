/**
 * Execution panel for real-time logs
 */

import React, { useRef, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  DrawerHeader,
  DrawerBody,
  DrawerCloseButton,
  Spinner,
  Code,
  Divider,
  IconButton,
  Button,
  useToast,
} from '@chakra-ui/react';

interface ExecutionPanelProps {
  logs: string[];
  status?: string;
  onClose: () => void;
}

export const ExecutionPanel: React.FC<ExecutionPanelProps> = ({
  logs,
  status,
  onClose,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const toast = useToast();

  // Auto-scroll to bottom on new logs
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleCopyLogs = () => {
    const logText = logs.join('\n');
    navigator.clipboard.writeText(logText);
    toast({
      title: 'Logs copied',
      description: 'Execution logs have been copied to clipboard',
      status: 'success',
      duration: 2000,
      isClosable: true,
    });
  };

  const handleDownloadLogs = () => {
    const logText = logs.join('\n');
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execution-logs-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: 'Logs downloaded',
      description: 'Execution logs have been downloaded',
      status: 'success',
      duration: 2000,
      isClosable: true,
    });
  };

  const isRunning = status === 'executing' || status === 'validating';

  return (
    <>
      <DrawerCloseButton />
      <DrawerHeader borderBottomWidth="1px">
        <HStack justify="space-between" width="100%">
          <HStack spacing={3}>
            <Text>Execution Logs</Text>
            {isRunning && <Spinner size="sm" color="ocean.500" />}
            {status && (
              <Badge colorScheme={getStatusColor(status)}>
                {getStatusLabel(status)}
              </Badge>
            )}
          </HStack>
          <HStack spacing={2}>
            <Button size="sm" variant="ghost" onClick={handleCopyLogs}>
              Copy
            </Button>
            <Button size="sm" variant="ghost" onClick={handleDownloadLogs}>
              Download
            </Button>
          </HStack>
        </HStack>
      </DrawerHeader>

      <DrawerBody>
        <VStack align="stretch" spacing={2}>
          {logs.length === 0 ? (
            <Box textAlign="center" py={8}>
              <Text color="gray.500">No logs yet...</Text>
              {isRunning && (
                <Text color="gray.400" fontSize="sm" mt={2}>
                  Waiting for execution to start...
                </Text>
              )}
            </Box>
          ) : (
            <Box
              bg="gray.900"
              borderRadius="lg"
              p={4}
              fontFamily="mono"
              fontSize="sm"
              overflowX="auto"
              maxH="calc(100vh - 200px)"
              overflowY="auto"
            >
              {logs.map((log, index) => (
                <LogLine key={index} log={log} index={index} />
              ))}
              <div ref={bottomRef} />
            </Box>
          )}
        </VStack>
      </DrawerBody>
    </>
  );
};

interface LogLineProps {
  log: string;
  index: number;
}

const LogLine: React.FC<LogLineProps> = ({ log, index }) => {
  const { level, message, timestamp } = parseLog(log);

  return (
    <HStack
      spacing={3}
      align="flex-start"
      mb={1}
      _hover={{ bg: 'whiteAlpha.50' }}
      px={2}
      py={1}
      borderRadius="md"
    >
      <Text color="gray.500" fontSize="xs" minW="35px">
        {String(index + 1).padStart(3, '0')}
      </Text>
      {timestamp && (
        <Text color="gray.400" fontSize="xs" minW="80px">
          {timestamp}
        </Text>
      )}
      <Badge
        colorScheme={getLogLevelColor(level)}
        fontSize="xs"
        minW="50px"
        textAlign="center"
      >
        {level}
      </Badge>
      <Text color="gray.100" flex="1" wordBreak="break-word">
        {message}
      </Text>
    </HStack>
  );
};

// Helper functions
function parseLog(log: string): {
  level: string;
  message: string;
  timestamp?: string;
} {
  // Try to parse structured log format
  const timestampMatch = log.match(/^\[(\d{2}:\d{2}:\d{2})\]/);
  const levelMatch = log.match(/\[(INFO|WARN|ERROR|DEBUG)\]/i);

  let timestamp = timestampMatch ? timestampMatch[1] : undefined;
  let level = levelMatch ? levelMatch[1].toUpperCase() : 'INFO';
  let message = log;

  // Remove timestamp and level from message
  if (timestampMatch) {
    message = message.substring(timestampMatch[0].length).trim();
  }
  if (levelMatch) {
    message = message.replace(levelMatch[0], '').trim();
  }

  return { level, message, timestamp };
}

function getLogLevelColor(level: string): string {
  switch (level.toUpperCase()) {
    case 'ERROR':
      return 'red';
    case 'WARN':
    case 'WARNING':
      return 'orange';
    case 'DEBUG':
      return 'purple';
    default:
      return 'green';
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    case 'executing':
    case 'validating':
      return 'blue';
    default:
      return 'gray';
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'validating':
      return 'Validating';
    case 'executing':
      return 'Running';
    case 'completed':
      return 'Complete';
    case 'failed':
      return 'Failed';
    default:
      return status;
  }
}