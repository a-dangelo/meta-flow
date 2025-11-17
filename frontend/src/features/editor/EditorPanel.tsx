/**
 * EditorPanel Component
 * Monaco editor for workflow specifications with lazy loading
 */

import { Suspense, lazy, useCallback, useRef } from 'react';
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
  useColorModeValue,
  Input,
} from '@chakra-ui/react';
import {
  CopyIcon,
  DownloadIcon,
  DeleteIcon,
  RepeatIcon,
  InfoIcon,
  AttachmentIcon,
} from '@chakra-ui/icons';
import { useExamples } from '@/hooks/useExamples';

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
export const DEFAULT_TEMPLATE = `Workflow: My Workflow
Description: Enter your workflow description here

Inputs:
- input_param (string): Description of input

Steps:
1. First step description
2. Second step description

Outputs:
- result (string): Description of output`;

/**
 * EditorPanel component - Fully controlled by parent
 */
export function EditorPanel({
  value,
  onChange,
  onSubmit,
  isGenerating = false,
}: EditorPanelProps) {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { examples = [], loading: examplesLoading, selectedExample, selectExample } = useExamples();

  // Dark mode color values
  const toolbarBg = useColorModeValue('gray.50', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const editorTheme = useColorModeValue('vs-light', 'vs-dark');
  const spinnerBg = useColorModeValue('gray.50', 'gray.800');

  /**
   * Handle example selection
   */
  const handleExampleSelect = useCallback(
    (exampleName: string) => {
      if (!exampleName) {
        selectExample(null);
        return;
      }

      const example = examples?.find((ex) => ex.name === exampleName);
      if (example) {
        selectExample(example);
        onChange(example.content);
        toast({
          title: 'Example loaded',
          description: `Loaded "${example.name}" example`,
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
      }
    },
    [examples, selectExample, onChange, toast]
  );

  /**
   * Handle file upload
   */
  const handleFileUpload = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      if (!file.name.endsWith('.txt')) {
        toast({
          title: 'Invalid file type',
          description: 'Please select a .txt file',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        onChange(content);
        toast({
          title: 'File uploaded',
          description: `Loaded "${file.name}"`,
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
      };
      reader.onerror = () => {
        toast({
          title: 'Upload failed',
          description: 'Could not read the file',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
      };
      reader.readAsText(file);

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [onChange, toast]
  );

  /**
   * Copy to clipboard
   */
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(value);
    toast({
      title: 'Copied to clipboard',
      status: 'success',
      duration: 2000,
      isClosable: true,
    });
  }, [value, toast]);

  /**
   * Download as file
   */
  const handleDownload = useCallback(() => {
    const blob = new Blob([value], { type: 'text/plain' });
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
  }, [value, toast]);

  /**
   * Clear editor
   */
  const handleClear = useCallback(() => {
    onChange('');
    selectExample(null);
    toast({
      title: 'Editor cleared',
      status: 'info',
      duration: 2000,
      isClosable: true,
    });
  }, [onChange, selectExample, toast]);

  /**
   * Reset to template
   */
  const handleReset = useCallback(() => {
    onChange(DEFAULT_TEMPLATE);
    selectExample(null);
    toast({
      title: 'Reset to template',
      status: 'info',
      duration: 2000,
      isClosable: true,
    });
  }, [onChange, selectExample, toast]);

  /**
   * Handle editor change - directly pass to parent
   */
  const handleEditorChange = useCallback(
    (newValue: string | undefined) => {
      if (newValue !== undefined) {
        onChange(newValue);
      }
    },
    [onChange]
  );

  return (
    <VStack spacing={4} align="stretch">
      {/* Toolbar */}
      <Box bg={toolbarBg} p={3} borderRadius="md">
        <Flex align="center" gap={3}>
          {/* Example selector */}
          <Select
            placeholder="Load example..."
            value={selectedExample?.name || ''}
            onChange={(e) => handleExampleSelect(e.target.value)}
            isDisabled={examplesLoading || isGenerating}
            maxW="250px"
            size="sm"
          >
            {examples?.map((example) => (
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
            {/* File upload */}
            <Input
              ref={fileInputRef}
              type="file"
              accept=".txt"
              onChange={handleFileUpload}
              display="none"
              id="file-upload"
            />
            <Tooltip label="Upload file">
              <IconButton
                aria-label="Upload"
                icon={<AttachmentIcon />}
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                isDisabled={isGenerating}
              />
            </Tooltip>

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
      <Box
        border="1px solid"
        borderColor={borderColor}
        borderRadius="md"
        overflow="hidden"
        height="400px"
        minH="400px"
      >
        <Suspense
          fallback={
            <Flex align="center" justify="center" height="100%" bg={spinnerBg}>
              <VStack spacing={3}>
                <Spinner size="xl" color="blue.500" />
                <Text color="gray.600">Loading editor...</Text>
              </VStack>
            </Flex>
          }
        >
          <MonacoEditor
            height="400px"
            defaultLanguage="plaintext"
            value={value}
            onChange={handleEditorChange}
            theme={editorTheme}
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
          isDisabled={!value.trim() || isGenerating}
        >
          Generate Agent
        </Button>
      )}
    </VStack>
  );
}

export default EditorPanel;