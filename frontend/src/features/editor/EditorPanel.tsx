/**
 * EditorPanel Component
 * Monaco editor for workflow specifications with lazy loading
 */

import { Suspense, lazy, useState, useCallback, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Select,
  Button,
  Text,
  Spinner,
  useToast,
  IconButton,
  Tooltip,
  Flex,
  Badge,
  Spacer,
} from '@chakra-ui/react';
import {
  CopyIcon,
  DownloadIcon,
  DeleteIcon,
  RepeatIcon,
  InfoIcon,
} from '@chakra-ui/icons';
import { useExamples } from '@/hooks/useExamples';
import { useLocalStorage } from '@/hooks/useLocalStorage';

// Lazy load Monaco Editor (5MB bundle)
const MonacoEditor = lazy(() => import('@monaco-editor/react'));

interface EditorPanelProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  isGenerating?: boolean;
}

/**
 * Default editor template
 */
const DEFAULT_TEMPLATE = `Workflow: My Workflow
Description: Enter your workflow description here

Inputs:
- input_param (string): Description of input

Steps:
1. First step description
2. Second step description

Outputs:
- result (string): Description of output`;

/**
 * EditorPanel component
 */
export function EditorPanel({
  value,
  onChange,
  onSubmit,
  isGenerating = false,
}: EditorPanelProps) {
  const toast = useToast();
  const { examples, loading: examplesLoading, selectedExample, selectExample } = useExamples();
  const [editorContent, setEditorContent] = useLocalStorage('meta-flow-editor-content', value || DEFAULT_TEMPLATE);
  const [selectedExampleName, setSelectedExampleName] = useState<string>('');

  // Sync editor content with parent
  useEffect(() => {
    onChange(editorContent);
  }, [editorContent, onChange]);

  // Sync value prop with editor
  useEffect(() => {
    if (value !== editorContent) {
      setEditorContent(value);
    }
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  /**
   * Handle example selection
   */
  const handleExampleSelect = useCallback(
    (exampleName: string) => {
      if (!exampleName) {
        selectExample(null);
        setSelectedExampleName('');
        return;
      }

      const example = examples.find((ex) => ex.name === exampleName);
      if (example) {
        selectExample(example);
        setSelectedExampleName(exampleName);
        setEditorContent(example.content);
        toast({
          title: 'Example loaded',
          description: `Loaded "${example.name}" example`,
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
      }
    },
    [examples, selectExample, setEditorContent, toast]
  );

  /**
   * Copy to clipboard
   */
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(editorContent);
    toast({
      title: 'Copied to clipboard',
      status: 'success',
      duration: 2000,
      isClosable: true,
    });
  }, [editorContent, toast]);

  /**
   * Download as file
   */
  const handleDownload = useCallback(() => {
    const blob = new Blob([editorContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: 'File downloaded',
      status: 'success',
      duration: 2000,
      isClosable: true,
    });
  }, [editorContent, toast]);

  /**
   * Clear editor
   */
  const handleClear = useCallback(() => {
    setEditorContent(DEFAULT_TEMPLATE);
    selectExample(null);
    setSelectedExampleName('');
    toast({
      title: 'Editor cleared',
      status: 'info',
      duration: 2000,
      isClosable: true,
    });
  }, [setEditorContent, selectExample, toast]);

  /**
   * Reset to template
   */
  const handleReset = useCallback(() => {
    setEditorContent(DEFAULT_TEMPLATE);
    selectExample(null);
    setSelectedExampleName('');
    toast({
      title: 'Reset to template',
      status: 'info',
      duration: 2000,
      isClosable: true,
    });
  }, [setEditorContent, selectExample, toast]);

  /**
   * Handle editor change
   */
  const handleEditorChange = useCallback(
    (newValue: string | undefined) => {
      if (newValue !== undefined) {
        setEditorContent(newValue);
      }
    },
    [setEditorContent]
  );

  return (
    <VStack spacing={4} align="stretch" height="100%">
      {/* Toolbar */}
      <Box bg="gray.50" p={3} borderRadius="md">
        <Flex align="center" gap={3}>
          {/* Example selector */}
          <Select
            placeholder="Load example..."
            value={selectedExampleName}
            onChange={(e) => handleExampleSelect(e.target.value)}
            isDisabled={examplesLoading || isGenerating}
            maxW="250px"
            size="sm"
          >
            {examples.map((example) => (
              <option key={example.name} value={example.name}>
                {example.name} ({example.type})
              </option>
            ))}
          </Select>

          {/* Selected example info */}
          {selectedExample && (
            <Tooltip label={selectedExample.description}>
              <Badge colorScheme="blue" variant="subtle">
                <HStack spacing={1}>
                  <InfoIcon boxSize={3} />
                  <Text>{selectedExample.type}</Text>
                </HStack>
              </Badge>
            </Tooltip>
          )}

          <Spacer />

          {/* Action buttons */}
          <HStack spacing={2}>
            <Tooltip label="Copy to clipboard">
              <IconButton
                aria-label="Copy"
                icon={<CopyIcon />}
                size="sm"
                onClick={handleCopy}
                isDisabled={isGenerating}
              />
            </Tooltip>

            <Tooltip label="Download as file">
              <IconButton
                aria-label="Download"
                icon={<DownloadIcon />}
                size="sm"
                onClick={handleDownload}
                isDisabled={isGenerating}
              />
            </Tooltip>

            <Tooltip label="Reset to template">
              <IconButton
                aria-label="Reset"
                icon={<RepeatIcon />}
                size="sm"
                onClick={handleReset}
                isDisabled={isGenerating}
              />
            </Tooltip>

            <Tooltip label="Clear editor">
              <IconButton
                aria-label="Clear"
                icon={<DeleteIcon />}
                size="sm"
                colorScheme="red"
                variant="ghost"
                onClick={handleClear}
                isDisabled={isGenerating}
              />
            </Tooltip>
          </HStack>
        </Flex>
      </Box>

      {/* Monaco Editor */}
      <Box flex={1} border="1px solid" borderColor="gray.200" borderRadius="md" overflow="hidden">
        <Suspense
          fallback={
            <Flex align="center" justify="center" height="100%" bg="gray.50">
              <VStack spacing={3}>
                <Spinner size="xl" color="blue.500" />
                <Text color="gray.600">Loading editor...</Text>
              </VStack>
            </Flex>
          }
        >
          <MonacoEditor
            height="100%"
            defaultLanguage="plaintext"
            value={editorContent}
            onChange={handleEditorChange}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              wordWrap: 'on',
              automaticLayout: true,
              scrollBeyondLastLine: false,
              renderWhitespace: 'selection',
              readOnly: isGenerating,
              quickSuggestions: false,
              suggestOnTriggerCharacters: false,
              tabSize: 2,
            }}
          />
        </Suspense>
      </Box>

      {/* Submit button */}
      {onSubmit && (
        <Button
          colorScheme="blue"
          size="lg"
          onClick={onSubmit}
          isLoading={isGenerating}
          loadingText="Generating..."
          isDisabled={!editorContent.trim() || isGenerating}
        >
          Generate Agent
        </Button>
      )}
    </VStack>
  );
}

export default EditorPanel;