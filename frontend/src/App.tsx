/**
 * Main App Component
 * Integrates all features for the Meta-Flow agent generation pipeline
 */

import { useState, useCallback, useEffect } from 'react';
import {
  ChakraProvider,
  Box,
  Container,
  VStack,
  HStack,
  Heading,
  Text,
  Grid,
  GridItem,
  useToast,
  Flex,
  Spacer,
  IconButton,
  Tooltip,
  Badge,
  Alert,
  AlertIcon,
  useColorMode,
  useColorModeValue,
} from '@chakra-ui/react';
import { MoonIcon, SunIcon, InfoIcon } from '@chakra-ui/icons';
import ErrorBoundary from '@/components/ErrorBoundary';
import { EditorPanel } from '@/features/editor';
import { PipelineVisualizer } from '@/features/pipeline';
import { OutputPanel } from '@/features/output';
import { useGenerate } from '@/hooks/useGenerate';
import { checkHealth } from '@/services/api';
import { APP_VERSION } from '@/config/env';

/**
 * Main App component
 */
function App() {
  const toast = useToast();
  const { colorMode, toggleColorMode } = useColorMode();
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');

  // State
  const [editorContent, setEditorContent] = useState('');
  const [healthStatus, setHealthStatus] = useState<'checking' | 'healthy' | 'error'>('checking');
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false);

  // Hooks
  const {
    isGenerating,
    currentStage,
    progress,
    error,
    lastResult,
    generate,
    cancel,
    reset,
  } = useGenerate();

  /**
   * Check backend health on mount
   */
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const health = await checkHealth();
        setHealthStatus('healthy');
        setApiKeyConfigured(health.checks.api_key_configured);

        if (!health.checks.api_key_configured) {
          toast({
            title: 'API Key Required',
            description: 'Please set ANTHROPIC_API_KEY, AIMLAPI_KEY, or GEMINI_API_KEY in backend .env file',
            status: 'warning',
            duration: null,
            isClosable: true,
          });
        }
      } catch (err) {
        setHealthStatus('error');
        toast({
          title: 'Backend Connection Failed',
          description: 'Please ensure the backend server is running on http://localhost:8000',
          status: 'error',
          duration: null,
          isClosable: true,
        });
      }
    };

    checkBackendHealth();
  }, [toast]);

  /**
   * Handle generation submission
   */
  const handleGenerate = useCallback(async () => {
    if (!editorContent.trim()) {
      toast({
        title: 'No specification provided',
        description: 'Please enter a workflow specification',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    // Reset previous state
    reset();

    // Start generation
    const result = await generate({
      spec: editorContent,
      provider: 'claude', // Default provider
    });

    if (result) {
      toast({
        title: 'Agent Generated Successfully',
        description: `Generated ${result.workflow_name} (${result.workflow_type})`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [editorContent, generate, reset, toast]);

  /**
   * Handle generation cancellation
   */
  const handleCancel = useCallback(() => {
    cancel();
    toast({
      title: 'Generation Cancelled',
      status: 'info',
      duration: 2000,
      isClosable: true,
    });
  }, [cancel, toast]);

  return (
    <ChakraProvider>
      <ErrorBoundary>
        <Box minH="100vh" bg={bgColor}>
          {/* Header */}
          <Box bg={cardBg} borderBottom="1px" borderColor="gray.200" py={4}>
            <Container maxW="container.xl">
              <Flex align="center">
                <HStack spacing={4}>
                  <Heading size="lg">Meta-Flow Agent Generator</Heading>
                  <Badge colorScheme="blue" variant="subtle">
                    v{APP_VERSION}
                  </Badge>
                </HStack>

                <Spacer />

                <HStack spacing={3}>
                  {/* Health status indicator */}
                  <HStack>
                    <Text fontSize="sm" color="gray.600">
                      Backend:
                    </Text>
                    <Badge
                      colorScheme={
                        healthStatus === 'healthy'
                          ? 'green'
                          : healthStatus === 'error'
                          ? 'red'
                          : 'gray'
                      }
                    >
                      {healthStatus === 'healthy'
                        ? apiKeyConfigured
                          ? 'Ready'
                          : 'No API Key'
                        : healthStatus === 'error'
                        ? 'Disconnected'
                        : 'Checking...'}
                    </Badge>
                  </HStack>

                  {/* Info button */}
                  <Tooltip label="About Meta-Flow">
                    <IconButton
                      aria-label="Info"
                      icon={<InfoIcon />}
                      variant="ghost"
                      onClick={() => {
                        toast({
                          title: 'Meta-Flow Agent Generator',
                          description:
                            'Transform natural language workflow specifications into executable Python agents. Supports sequential, conditional, parallel, orchestrator, and nested workflows.',
                          status: 'info',
                          duration: 8000,
                          isClosable: true,
                        });
                      }}
                    />
                  </Tooltip>

                  {/* Color mode toggle */}
                  <Tooltip label="Toggle color mode">
                    <IconButton
                      aria-label="Toggle color mode"
                      icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
                      onClick={toggleColorMode}
                      variant="ghost"
                    />
                  </Tooltip>
                </HStack>
              </Flex>
            </Container>
          </Box>

          {/* Main content */}
          <Container maxW="container.xl" py={6}>
            {healthStatus === 'error' ? (
              <Alert status="error" borderRadius="md">
                <AlertIcon />
                <VStack align="start" spacing={2}>
                  <Text fontWeight="bold">Backend Connection Error</Text>
                  <Text>
                    Unable to connect to the backend server. Please ensure:
                  </Text>
                  <Text fontSize="sm" as="ul" pl={4}>
                    <li>Backend is running: cd /workspaces/meta-flow && uvicorn api.main:app --reload</li>
                    <li>API is accessible at http://localhost:8000</li>
                    <li>Environment variables are configured in .env file</li>
                  </Text>
                </VStack>
              </Alert>
            ) : (
              <Grid templateColumns={{ base: '1fr', lg: '3fr 2fr' }} gap={6}>
                {/* Left column: Editor and Pipeline */}
                <GridItem>
                  <VStack spacing={6} align="stretch">
                    {/* Editor Panel */}
                    <Box bg={cardBg} p={4} borderRadius="md" shadow="sm" minH="500px">
                      <EditorPanel
                        value={editorContent}
                        onChange={setEditorContent}
                        onSubmit={isGenerating ? handleCancel : handleGenerate}
                        isGenerating={isGenerating}
                      />
                    </Box>
                  </VStack>
                </GridItem>

                {/* Right column: Pipeline Status and Output */}
                <GridItem>
                  <VStack spacing={6} align="stretch">
                    {/* Pipeline Visualizer */}
                    <Box bg={cardBg} p={4} borderRadius="md" shadow="sm">
                      <PipelineVisualizer
                        currentStage={currentStage}
                        progress={progress}
                        error={error}
                        executionTime={lastResult?.execution_time}
                      />
                    </Box>

                    {/* Output Panel */}
                    <Box bg={cardBg} p={4} borderRadius="md" shadow="sm" minH="400px">
                      <OutputPanel
                        result={lastResult}
                        isLoading={isGenerating}
                        error={error}
                        colorMode={colorMode}
                      />
                    </Box>
                  </VStack>
                </GridItem>
              </Grid>
            )}
          </Container>

          {/* Footer */}
          <Box bg={cardBg} borderTop="1px" borderColor="gray.200" py={4} mt={8}>
            <Container maxW="container.xl">
              <Text fontSize="sm" color="gray.600" textAlign="center">
                Meta-Flow Agent Generator • Transform workflow specifications into executable agents
              </Text>
            </Container>
          </Box>
        </Box>
      </ErrorBoundary>
    </ChakraProvider>
  );
}

export default App;