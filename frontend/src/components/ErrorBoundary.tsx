/**
 * ErrorBoundary Component
 * CRITICAL: Required for production React 18 applications
 * Catches JavaScript errors in child component tree and displays fallback UI
 */

import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import {
  Box,
  Text,
  Button,
  VStack,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Code,
  Collapse,
  useDisclosure,
  Container,
} from '@chakra-ui/react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error details component for development mode
 */
function ErrorDetails({ error, errorInfo }: { error: Error; errorInfo: ErrorInfo }) {
  const { isOpen, onToggle } = useDisclosure();

  return (
    <VStack spacing={4} align="stretch">
      <Button onClick={onToggle} variant="ghost" size="sm">
        {isOpen ? 'Hide' : 'Show'} Error Details
      </Button>
      <Collapse in={isOpen}>
        <VStack spacing={3} align="stretch">
          <Box>
            <Text fontWeight="bold" mb={1}>Error Message:</Text>
            <Code p={2} display="block" whiteSpace="pre-wrap">
              {error.toString()}
            </Code>
          </Box>
          <Box>
            <Text fontWeight="bold" mb={1}>Stack Trace:</Text>
            <Code
              p={2}
              display="block"
              whiteSpace="pre-wrap"
              fontSize="xs"
              maxH="200px"
              overflowY="auto"
            >
              {error.stack}
            </Code>
          </Box>
          <Box>
            <Text fontWeight="bold" mb={1}>Component Stack:</Text>
            <Code
              p={2}
              display="block"
              whiteSpace="pre-wrap"
              fontSize="xs"
              maxH="200px"
              overflowY="auto"
            >
              {errorInfo.componentStack}
            </Code>
          </Box>
        </VStack>
      </Collapse>
    </VStack>
  );
}

/**
 * Main ErrorBoundary class component
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to console
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Update state with error details
    this.setState({
      errorInfo,
    });

    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // In production, you might want to log to an error reporting service
    if (import.meta.env.PROD) {
      // Example: logErrorToService(error, errorInfo);
      console.error('Production error logged:', {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
      });
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    // Optionally reload the page
    // window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback provided
      if (this.props.fallback) {
        return <>{this.props.fallback}</>;
      }

      const { error, errorInfo } = this.state;

      // Default error UI
      return (
        <Container maxW="container.md" py={10}>
          <Alert
            status="error"
            variant="subtle"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            textAlign="center"
            minHeight="200px"
            borderRadius="lg"
            p={6}
          >
            <AlertIcon boxSize="40px" mr={0} />
            <AlertTitle mt={4} mb={1} fontSize="lg">
              Application Error
            </AlertTitle>
            <AlertDescription maxWidth="sm">
              <VStack spacing={4}>
                <Text>
                  Something went wrong while rendering this application.
                  Please try refreshing the page or contact support if the problem persists.
                </Text>

                <Button
                  colorScheme="red"
                  variant="solid"
                  onClick={this.handleReset}
                  size="md"
                >
                  Try Again
                </Button>

                {/* Show error details in development */}
                {import.meta.env.DEV && error && errorInfo && (
                  <Box w="full" mt={4}>
                    <ErrorDetails error={error} errorInfo={errorInfo} />
                  </Box>
                )}
              </VStack>
            </AlertDescription>
          </Alert>
        </Container>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook for using error boundary functionality
 * Note: This doesn't catch errors, it's for triggering error boundary from hooks
 */
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return setError;
}

export default ErrorBoundary;