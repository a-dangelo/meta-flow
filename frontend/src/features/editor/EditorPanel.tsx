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
  AttachmentIcon,
  StarIcon,
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
    <VStack spacing={5} align="stretch">
      {/* Enhanced Toolbar */}
      <Box
        bg={useColorModeValue('white', 'gray.800')}
        p={4}
        borderRadius="lg"
        border="1px solid"
        borderColor={useColorModeValue('gray.200', 'gray.600')}
        shadow="sm"
      >
        <Flex align="center" gap={3} flexWrap={{ base: 'wrap', md: 'nowrap' }}>
          {/* Example selector */}
          <Select
            placeholder="Load example..."
            value={selectedExample?.name || ''}
            onChange={(e) => handleExampleSelect(e.target.value)}
            isDisabled={examplesLoading || isGenerating}
            maxW={{ base: '100%', md: '280px' }}
            size="sm"
            borderRadius="md"
            _hover={{
              borderColor: 'blue.400',
            }}
            _focus={{
              borderColor: 'blue.500',
              boxShadow: '0 0 0 1px rgba(66, 153, 225, 0.6)',
            }}
          >
            {examples?.map((example) => (
              <option key={example.name} value={example.name}>
                {example.name} ({example.type})
              </option>
            ))}
          </Select>

          {/* Selected example info */}
          {selectedExample && (
            <Tooltip label={selectedExample.description} hasArrow>
              <Badge
                colorScheme="blue"
                variant="subtle"
                px={3}
                py={1}
                borderRadius="full"
              >
                <HStack spacing={1}>
                  <StarIcon boxSize={3} />
                  <Text fontSize="xs" fontWeight="600">{selectedExample.type}</Text>
                </HStack>
              </Badge>
            </Tooltip>
          )}

          <Spacer display={{ base: 'none', md: 'block' }} />

          {/* Action buttons */}
          <HStack spacing={2} flexWrap="wrap">
            {/* File upload */}
            <Input
              ref={fileInputRef}
              type="file"
              accept=".txt"
              onChange={handleFileUpload}
              display="none"
              id="file-upload"
            />
            <Tooltip label="Upload file" hasArrow>
              <IconButton
                aria-label="Upload"
                icon={<AttachmentIcon />}
                size="sm"
                variant="ghost"
                onClick={() => fileInputRef.current?.click()}
                isDisabled={isGenerating}
                _hover={{
                  bg: useColorModeValue('gray.100', 'gray.700'),
                  transform: 'translateY(-2px)',
                }}
                _active={{
                  transform: 'translateY(0)',
                }}
                transition="all 0.15s"
              />
            </Tooltip>

            <Tooltip label="Copy to clipboard" hasArrow>
              <IconButton
                aria-label="Copy"
                icon={<CopyIcon />}
                size="sm"
                variant="ghost"
                onClick={handleCopy}
                isDisabled={isGenerating}
                _hover={{
                  bg: useColorModeValue('gray.100', 'gray.700'),
                  transform: 'translateY(-2px)',
                }}
                _active={{
                  transform: 'translateY(0)',
                }}
                transition="all 0.15s"
              />
            </Tooltip>

            <Tooltip label="Download as file" hasArrow>
              <IconButton
                aria-label="Download"
                icon={<DownloadIcon />}
                size="sm"
                variant="ghost"
                onClick={handleDownload}
                isDisabled={isGenerating}
                _hover={{
                  bg: useColorModeValue('gray.100', 'gray.700'),
                  transform: 'translateY(-2px)',
                }}
                _active={{
                  transform: 'translateY(0)',
                }}
                transition="all 0.15s"
              />
            </Tooltip>

            <Tooltip label="Reset to template" hasArrow>
              <IconButton
                aria-label="Reset"
                icon={<RepeatIcon />}
                size="sm"
                variant="ghost"
                onClick={handleReset}
                isDisabled={isGenerating}
                _hover={{
                  bg: useColorModeValue('gray.100', 'gray.700'),
                  transform: 'translateY(-2px)',
                }}
                _active={{
                  transform: 'translateY(0)',
                }}
                transition="all 0.15s"
              />
            </Tooltip>

            <Tooltip label="Clear editor" hasArrow>
              <IconButton
                aria-label="Clear"
                icon={<DeleteIcon />}
                size="sm"
                colorScheme="red"
                variant="ghost"
                onClick={handleClear}
                isDisabled={isGenerating}
                _hover={{
                  bg: useColorModeValue('red.50', 'red.900'),
                  transform: 'translateY(-2px)',
                }}
                _active={{
                  transform: 'translateY(0)',
                }}
                transition="all 0.15s"
              />
            </Tooltip>
          </HStack>
        </Flex>
      </Box>

      {/* Monaco Editor */}
      <Box
        border="1px solid"
        borderColor={useColorModeValue('gray.300', 'gray.600')}
        borderRadius="lg"
        overflow="hidden"
        height="420px"
        minH="420px"
        shadow="sm"
        transition="all 0.2s"
        _hover={{
          borderColor: useColorModeValue('gray.400', 'gray.500'),
          shadow: 'md',
        }}
      >
        <Suspense
          fallback={
            <Flex align="center" justify="center" height="100%" bg={spinnerBg}>
              <VStack spacing={4}>
                <Spinner
                  size="xl"
                  color="blue.500"
                  thickness="3px"
                  speed="0.65s"
                />
                <Text color={useColorModeValue('gray.600', 'gray.400')} fontWeight="500">
                  Loading editor...
                </Text>
              </VStack>
            </Flex>
          }
        >
          <MonacoEditor
            height="420px"
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
              fontFamily: '"Fira Code", "Roboto Mono", monospace',
              fontLigatures: true,
            }}
          />
        </Suspense>
      </Box>

      {/* Enhanced Submit button */}
      {onSubmit && (
        <Button
          colorScheme="blue"
          size="lg"
          onClick={onSubmit}
          isLoading={isGenerating}
          loadingText="Generating Agent..."
          isDisabled={!value.trim() || isGenerating}
          width="100%"
          height="60px"
          fontSize="lg"
          fontWeight="bold"
          shadow="lg"
          bgGradient={
            !isGenerating
              ? useColorModeValue(
                  'linear(to-r, blue.500, blue.600)',
                  'linear(to-r, blue.400, blue.500)'
                )
              : undefined
          }
          _hover={
            !isGenerating
              ? {
                  transform: 'translateY(-2px)',
                  shadow: 'xl',
                  bgGradient: useColorModeValue(
                    'linear(to-r, blue.600, blue.700)',
                    'linear(to-r, blue.500, blue.600)'
                  ),
                }
              : {}
          }
          _active={{
            transform: 'translateY(0)',
            shadow: 'md',
          }}
          _disabled={{
            opacity: 0.4,
            cursor: 'not-allowed',
            bgGradient: 'none',
          }}
          transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
          leftIcon={!isGenerating ? <StarIcon boxSize={5} /> : undefined}
          letterSpacing="wide"
        >
          {isGenerating ? 'Generating Agent...' : 'Generate Agent'}
        </Button>
      )}
    </VStack>
  );
}

export default EditorPanel;