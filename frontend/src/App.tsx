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
  extendTheme,
  type ThemeConfig,
} from '@chakra-ui/react';
import { MoonIcon, SunIcon, InfoIcon } from '@chakra-ui/icons';
import ErrorBoundary from '@/components/ErrorBoundary';
import { EditorPanel, DEFAULT_TEMPLATE } from '@/features/editor';
import { PipelineVisualizer } from '@/features/pipeline';
import { OutputPanel } from '@/features/output';
import { useGenerate } from '@/hooks/useGenerate';
import { useLocalStorage } from '@/hooks/useLocalStorage';
import { checkHealth } from '@/services/api';
import { APP_VERSION } from '@/config/env';

/**
 * Configure Chakra UI theme with color mode support
 */
const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  styles: {
    global: (props: any) => ({
      body: {
        bg: props.colorMode === 'dark' ? '#0f1419' : '#f7fafc',
        color: props.colorMode === 'dark' ? 'gray.100' : 'gray.800',
        lineHeight: 'base',
      },
      'h1, h2, h3, h4, h5, h6': {
        letterSpacing: 'tight',
      },
    }),
  },
  components: {
    Heading: {
      baseStyle: {
        fontWeight: '700',
        letterSpacing: '-0.025em',
      },
    },
    Button: {
      baseStyle: {
        fontWeight: '600',
        letterSpacing: '0.025em',
      },
    },
    Badge: {
      baseStyle: {
        fontWeight: '600',
        px: 3,
        py: 1,
      },
    },
  },
  fontSizes: {
    xs: '0.75rem',
    sm: '0.875rem',
    md: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
  },
  lineHeights: {
    normal: 'normal',
    none: 1,
    shorter: 1.25,
    short: 1.375,
    base: 1.5,
    tall: 1.625,
    taller: 2,
  },
});

/**
 * Inner App component that uses color mode hooks
 */
function AppContent() {
  const toast = useToast();
  const { colorMode, toggleColorMode } = useColorMode();
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');

  // State with localStorage persistence
  const [editorContent, setEditorContent] = useLocalStorage(
    'meta-flow-editor-content',
    DEFAULT_TEMPLATE
  );
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
    <ErrorBoundary>
      <Box minH="100vh" bg={bgColor}>
          {/* Header */}
          <Box
            bg={useColorModeValue('rgba(255, 255, 255, 0.95)', 'rgba(15, 20, 25, 0.95)')}
            borderBottom="1px"
            borderColor={useColorModeValue('gray.300', 'gray.700')}
            py={5}
            position="sticky"
            top={0}
            zIndex={10}
            backdropFilter="blur(10px)"
            boxShadow="sm"
          >
            <Container maxW="container.xl">
              <Flex align="center">
                <HStack spacing={4}>
                  <Heading
                    size="xl"
                    fontWeight="800"
                    bgGradient={useColorModeValue(
                      'linear(to-r, blue.600, purple.500)',
                      'linear(to-r, blue.300, purple.300)'
                    )}
                    bgClip="text"
                  >
                    Meta-Flow Agent Generator
                  </Heading>
                  <Badge
                    colorScheme="blue"
                    variant="subtle"
                    fontSize="md"
                    borderRadius="full"
                  >
                    v{APP_VERSION}
                  </Badge>
                </HStack>

                <Spacer />

                <HStack spacing={4}>
                  {/* Enhanced health status indicator */}
                  <HStack
                    spacing={2}
                    px={3}
                    py={2}
                    bg={useColorModeValue('gray.50', 'gray.700')}
                    borderRadius="md"
                    border="1px solid"
                    borderColor={useColorModeValue('gray.200', 'gray.600')}
                  >
                    <Text fontSize="sm" fontWeight="600" color="gray.600">
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
                      variant="solid"
                      fontSize="xs"
                      borderRadius="full"
                    >
                      {healthStatus === 'healthy'
                        ? apiKeyConfigured
                          ? '● Ready'
                          : '○ No API Key'
                        : healthStatus === 'error'
                        ? '✕ Disconnected'
                        : '○ Checking...'}
                    </Badge>
                  </HStack>

                  {/* Info button */}
                  <Tooltip label="About Meta-Flow" hasArrow placement="bottom">
                    <IconButton
                      aria-label="Info"
                      icon={<InfoIcon />}
                      variant="ghost"
                      size="md"
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
                      _hover={{
                        bg: useColorModeValue('blue.50', 'blue.900'),
                        transform: 'scale(1.05)',
                      }}
                      transition="all 0.2s"
                    />
                  </Tooltip>

                  {/* Color mode toggle */}
                  <Tooltip label="Toggle color mode" hasArrow placement="bottom">
                    <IconButton
                      aria-label="Toggle color mode"
                      icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
                      onClick={toggleColorMode}
                      variant="ghost"
                      size="md"
                      _hover={{
                        bg: useColorModeValue('purple.50', 'purple.900'),
                        transform: 'rotate(20deg) scale(1.05)',
                      }}
                      transition="all 0.2s"
                    />
                  </Tooltip>
                </HStack>
              </Flex>
            </Container>
          </Box>

          {/* Main content */}
          <Container maxW="container.xl" py={8} px={{ base: 4, md: 6, lg: 8 }}>
            {healthStatus === 'error' ? (
              <Alert status="error" borderRadius="lg" variant="left-accent">
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
              <VStack spacing={8} align="stretch" w="100%" maxW="100%">
                {/* Top row: Editor Panel (full width) */}
                <Box
                  bg={cardBg}
                  p={6}
                  borderRadius="lg"
                  shadow={useColorModeValue(
                    '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                    '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)'
                  )}
                  border="1px solid"
                  borderColor={useColorModeValue('gray.200', 'gray.700')}
                  borderTop="3px solid"
                  borderTopColor="blue.500"
                  w="100%"
                  transition="all 0.2s"
                  _hover={{
                    shadow: useColorModeValue(
                      '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                      '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)'
                    ),
                  }}
                >
                  <EditorPanel
                    value={editorContent}
                    onChange={setEditorContent}
                    onSubmit={isGenerating ? handleCancel : handleGenerate}
                    isGenerating={isGenerating}
                  />
                </Box>

                {/* Bottom row: Pipeline Status + Output */}
                <Grid templateColumns={{ base: '1fr', lg: '380px 1fr' }} gap={8} w="100%">
                  {/* Left: Pipeline Visualizer (fixed width) */}
                  <GridItem>
                    <Box
                      bg={cardBg}
                      p={6}
                      borderRadius="lg"
                      shadow={useColorModeValue(
                        '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                        '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)'
                      )}
                      border="1px solid"
                      borderColor={useColorModeValue('gray.200', 'gray.700')}
                      height="100%"
                      transition="all 0.2s"
                      _hover={{
                        shadow: useColorModeValue(
                          '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                          '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)'
                        ),
                      }}
                    >
                      <PipelineVisualizer
                        currentStage={currentStage}
                        progress={progress}
                        error={error}
                        executionTime={lastResult?.execution_time}
                      />
                    </Box>
                  </GridItem>

                  {/* Right: Output Panel (flexible width) */}
                  <GridItem overflow="hidden">
                    <Box
                      bg={cardBg}
                      p={6}
                      borderRadius="lg"
                      shadow={useColorModeValue(
                        '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                        '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)'
                      )}
                      border="1px solid"
                      borderColor={useColorModeValue('gray.200', 'gray.700')}
                      minH="500px"
                      transition="all 0.2s"
                      _hover={{
                        shadow: useColorModeValue(
                          '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                          '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)'
                        ),
                      }}
                    >
                      <OutputPanel
                        result={lastResult}
                        isLoading={isGenerating}
                        error={error}
                        colorMode={colorMode}
                      />
                    </Box>
                  </GridItem>
                </Grid>
              </VStack>
            )}
          </Container>

          {/* Footer */}
          <Box
            bg={cardBg}
            borderTop="1px"
            borderColor={useColorModeValue('gray.300', 'gray.700')}
            py={6}
            mt={12}
          >
            <Container maxW="container.xl">
              <Text
                fontSize="sm"
                color={useColorModeValue('gray.600', 'gray.400')}
                textAlign="center"
                letterSpacing="wide"
              >
                Meta-Flow Agent Generator • Transform workflow specifications into executable agents
              </Text>
            </Container>
          </Box>
        </Box>
      </ErrorBoundary>
  );
}

/**
 * Main App wrapper with ChakraProvider
 */
function App() {
  return (
    <ChakraProvider theme={theme}>
      <AppContent />
    </ChakraProvider>
  );
}

export default App;