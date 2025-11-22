/**
 * OutputPanel Component
 * Displays generated JSON and Python code in tabbed interface
 */

import { useState, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Text,
  IconButton,
  Tooltip,
  Badge,
  useToast,
  Flex,
  Spacer,
} from '@chakra-ui/react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { CopyIcon, DownloadIcon } from '@chakra-ui/icons';
import DOMPurify from 'dompurify';
import type { GenerateResponse } from '@/types';
import { LoadingState, ErrorState, EmptyState, CodeSkeleton } from '@/components';

interface OutputPanelProps {
  result: GenerateResponse | null;
  isLoading?: boolean;
  error?: string | null;
  colorMode?: 'light' | 'dark';
}

/**
 * OutputPanel component
 */
export function OutputPanel({
  result,
  isLoading = false,
  error,
  colorMode = 'light',
}: OutputPanelProps) {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState(0);
  const panelBorderColor = colorMode === 'dark' ? '#2a3038' : '#e0ddd4';
  const sectionBg = colorMode === 'dark' ? '#171c23' : '#fcfbf7';
  const insetBg = colorMode === 'dark' ? '#1d242c' : '#f5f2eb';
  const actionBg = colorMode === 'dark' ? '#1f252d' : '#faf8f2';
  const actionHoverBg = colorMode === 'dark' ? '#2a3038' : '#ebe6db';
  const mutedText = colorMode === 'dark' ? '#b7beca' : '#6f7378';

  /**
   * Copy code to clipboard
   */
  const handleCopy = useCallback(
    (content: string, type: string) => {
      // Sanitize content before copying
      const sanitized = DOMPurify.sanitize(content, { ALLOWED_TAGS: [] });
      navigator.clipboard.writeText(sanitized);

      toast({
        title: `${type} copied to clipboard`,
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    },
    [toast]
  );

  /**
   * Download code as file
   */
  const handleDownload = useCallback(
    (content: string, filename: string, mimeType: string) => {
      // Sanitize content before downloading
      const sanitized = DOMPurify.sanitize(content, { ALLOWED_TAGS: [] });
      const blob = new Blob([sanitized], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        title: 'File downloaded',
        description: filename,
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    },
    [toast]
  );

  /**
   * Format file size
   */
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Loading state with skeleton
  if (isLoading) {
    return (
      <VStack spacing={6} align="stretch">
        <LoadingState
          message="Generating agent..."
          submessage="This may take a few moments"
        />
        <Box p={6} borderRadius="md" bg={insetBg}>
          <CodeSkeleton lines={15} />
        </Box>
      </VStack>
    );
  }

  // Error state with enhanced UI
  if (error) {
    return (
      <ErrorState
        title="Generation Failed"
        message={error}
        suggestion="Check your workflow specification format and ensure the backend is running with a valid API key."
      />
    );
  }

  // No result state with empty state component
  if (!result) {
    return (
      <EmptyState
        title="No output yet"
        message="Enter a workflow specification and click 'Generate Agent' to see results."
      />
    );
  }

  const pythonCode = result.python_code || '';
  const jsonOutput = result.json_output || '{}';
  const syntaxTheme = colorMode === 'dark' ? vscDarkPlus : vs;

  // Parse JSON for pretty printing
  let formattedJson = jsonOutput;
  try {
    const parsed = JSON.parse(jsonOutput);
    formattedJson = JSON.stringify(parsed, null, 2);
  } catch {
    // Keep original if parsing fails
  }

  return (
    <VStack spacing={4} align="stretch" height="100%" w="100%" maxW="100%" overflow="hidden">
      {/* Header with metadata */}
      <Flex align="center" wrap="wrap" gap={2}>
        <HStack spacing={2}>
          <Text fontWeight="bold">Generated Agent:</Text>
          <Badge bg="#2c3a40" color="#f5f3ed" fontWeight="600">
            {result.workflow_name}
          </Badge>
          <Badge
            variant="outline"
            borderColor="#4f6b5a"
            color="#4f6b5a"
            fontWeight="600"
          >
            {result.workflow_type}
          </Badge>
        </HStack>
        <Spacer />
        {result.execution_time && (
          <Text fontSize="sm" color={mutedText}>
            Generated in {(result.execution_time / 1000).toFixed(2)}s
          </Text>
        )}
      </Flex>

      {/* Tabbed output */}
      <Tabs
        index={activeTab}
        onChange={setActiveTab}
        variant="enclosed"
        flex={1}
        display="flex"
        flexDirection="column"
        overflow="hidden"
      >
        <TabList>
          <Tab>
            <HStack spacing={2}>
              <Text>Python Code</Text>
              <Badge>{formatSize(pythonCode.length)}</Badge>
            </HStack>
          </Tab>
          <Tab>
            <HStack spacing={2}>
              <Text>JSON AST</Text>
              <Badge>{formatSize(formattedJson.length)}</Badge>
            </HStack>
          </Tab>
          {result.metadata && (
            <Tab>
              <Text>Metadata</Text>
            </Tab>
          )}
        </TabList>

        <TabPanels flex={1} display="flex" flexDirection="column">
          {/* Python Code Tab */}
          <TabPanel p={0} flex={1} display="flex" flexDirection="column" className="tab-transition">
            <Box
              flex={1}
              border="1px solid"
              borderColor={panelBorderColor}
              borderRadius="md"
              overflow="auto"
              position="relative"
              transition="all 0.2s ease-in-out"
              bg={sectionBg}
            >
              {/* Action buttons */}
              <HStack position="absolute" top={2} right={2} zIndex={1}>
                <Tooltip label="Copy Python code">
                  <IconButton
                    aria-label="Copy"
                    icon={<CopyIcon />}
                    size="sm"
                    onClick={() => handleCopy(pythonCode, 'Python code')}
                    bg={actionBg}
                    color={colorMode === 'dark' ? '#ecf0f2' : '#1f2a32'}
                    _hover={{ bg: actionHoverBg }}
                  />
                </Tooltip>
                <Tooltip label="Download as .py file">
                  <IconButton
                    aria-label="Download"
                    icon={<DownloadIcon />}
                    size="sm"
                    onClick={() =>
                      handleDownload(
                        pythonCode,
                        `${result.workflow_name.toLowerCase().replace(/\s+/g, '_')}_agent.py`,
                        'text/x-python'
                      )
                    }
                    bg={actionBg}
                    color={colorMode === 'dark' ? '#ecf0f2' : '#1f2a32'}
                    _hover={{ bg: actionHoverBg }}
                  />
                </Tooltip>
              </HStack>

              {/* Code display */}
              <Box p={4} overflowX="auto">
                <SyntaxHighlighter
                  language="python"
                  style={syntaxTheme}
                  showLineNumbers
                  wrapLongLines={false}
                  customStyle={{
                    margin: 0,
                    fontSize: '13px',
                    backgroundColor: 'transparent',
                    whiteSpace: 'pre',
                  }}
                >
                  {pythonCode}
                </SyntaxHighlighter>
              </Box>
            </Box>
          </TabPanel>

          {/* JSON AST Tab */}
          <TabPanel p={0} flex={1} display="flex" flexDirection="column" className="tab-transition">
            <Box
              flex={1}
              border="1px solid"
              borderColor={panelBorderColor}
              borderRadius="md"
              overflow="auto"
              position="relative"
              bg={sectionBg}
            >
              {/* Action buttons */}
              <HStack position="absolute" top={2} right={2} zIndex={1}>
                <Tooltip label="Copy JSON">
                  <IconButton
                    aria-label="Copy"
                    icon={<CopyIcon />}
                    size="sm"
                    onClick={() => handleCopy(formattedJson, 'JSON')}
                    bg={actionBg}
                    color={colorMode === 'dark' ? '#ecf0f2' : '#1f2a32'}
                    _hover={{ bg: actionHoverBg }}
                  />
                </Tooltip>
                <Tooltip label="Download as .json file">
                  <IconButton
                    aria-label="Download"
                    icon={<DownloadIcon />}
                    size="sm"
                    onClick={() =>
                      handleDownload(
                        formattedJson,
                        `${result.workflow_name.toLowerCase().replace(/\s+/g, '_')}_ast.json`,
                        'application/json'
                      )
                    }
                    bg={actionBg}
                    color={colorMode === 'dark' ? '#ecf0f2' : '#1f2a32'}
                    _hover={{ bg: actionHoverBg }}
                  />
                </Tooltip>
              </HStack>

              {/* JSON display */}
              <Box p={4} overflowX="auto">
                <SyntaxHighlighter
                  language="json"
                  style={syntaxTheme}
                  showLineNumbers
                  wrapLongLines={false}
                  customStyle={{
                    margin: 0,
                    fontSize: '13px',
                    backgroundColor: 'transparent',
                    whiteSpace: 'pre',
                  }}
                >
                  {formattedJson}
                </SyntaxHighlighter>
              </Box>
            </Box>
          </TabPanel>

          {/* Metadata Tab */}
          {result.metadata && (
            <TabPanel p={0} flex={1} display="flex" flexDirection="column" className="tab-transition">
              <Box
                flex={1}
                border="1px solid"
                borderColor={panelBorderColor}
                borderRadius="md"
                overflow="auto"
                bg={sectionBg}
              >
                <Box p={4} overflowX="auto">
                  <SyntaxHighlighter
                    language="json"
                    style={syntaxTheme}
                    wrapLongLines={false}
                    customStyle={{
                      margin: 0,
                      fontSize: '13px',
                      backgroundColor: 'transparent',
                      whiteSpace: 'pre',
                    }}
                  >
                    {JSON.stringify(result.metadata, null, 2)}
                  </SyntaxHighlighter>
                </Box>
              </Box>
            </TabPanel>
          )}
        </TabPanels>
      </Tabs>
    </VStack>
  );
}

export default OutputPanel;
