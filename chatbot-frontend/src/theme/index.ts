/**
 * Scandinavian Minimalist Theme for Chakra UI
 */

import { extendTheme } from '@chakra-ui/react';

const colors = {
  // Primary colors - Natural tones
  sand: {
    50: '#FDFBF7',
    100: '#F7F4EF', // Main background
    200: '#EDE7DD',
    300: '#DED3C4',
    400: '#C7B5A0',
    500: '#A89376',
    600: '#8B7355',
    700: '#6B5840',
    800: '#4A3D2C',
    900: '#2F2519',
  },
  ocean: {
    50: '#E8F4F8',
    100: '#C5E4ED',
    200: '#9FD3E2',
    300: '#6FBCD4',
    400: '#4AA5C4',
    500: '#1F6F8B', // Primary accent
    600: '#1A5A71',
    700: '#144558',
    800: '#0F3140',
    900: '#091E27',
  },
  sage: {
    50: '#F0F4F0',
    100: '#DDE6DD',
    200: '#C8D6C8',
    300: '#ACC1AC',
    400: '#8FA68F',
    500: '#708970', // Success/positive
    600: '#5A6E5A',
    700: '#455345',
    800: '#303930',
    900: '#1C211C',
  },
  clay: {
    50: '#FAF0ED',
    100: '#F3DDD4',
    200: '#EAC6B8',
    300: '#DFA897',
    400: '#D18872',
    500: '#C0634A', // Error/warning
    600: '#9E4D38',
    700: '#7A3A2A',
    800: '#56281D',
    900: '#341811',
  },
};

const fonts = {
  heading: '"Work Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  body: '"Manrope", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  mono: '"JetBrains Mono", "Fira Code", monospace',
};

const theme = extendTheme({
  colors,
  fonts,
  styles: {
    global: {
      'html, body': {
        backgroundColor: 'sand.100',
        color: 'gray.800',
        fontSize: '16px',
        lineHeight: '1.6',
      },
      '*::selection': {
        backgroundColor: 'ocean.100',
        color: 'ocean.900',
      },
    },
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: 500,
        borderRadius: 'md',
        transition: 'all 0.2s ease',
        _focus: {
          boxShadow: '0 0 0 3px rgba(31, 111, 139, 0.2)',
        },
      },
      variants: {
        solid: {
          bg: 'ocean.500',
          color: 'white',
          _hover: {
            bg: 'ocean.600',
            transform: 'translateY(-1px)',
          },
          _active: {
            bg: 'ocean.700',
            transform: 'translateY(0)',
          },
        },
        ghost: {
          color: 'ocean.600',
          _hover: {
            bg: 'ocean.50',
          },
          _active: {
            bg: 'ocean.100',
          },
        },
        outline: {
          borderColor: 'ocean.500',
          color: 'ocean.500',
          _hover: {
            bg: 'ocean.50',
          },
        },
      },
      sizes: {
        sm: {
          px: 3,
          py: 2,
          fontSize: 'sm',
        },
        md: {
          px: 4,
          py: 2.5,
          fontSize: 'md',
        },
        lg: {
          px: 6,
          py: 3,
          fontSize: 'lg',
        },
      },
      defaultProps: {
        variant: 'solid',
        size: 'md',
      },
    },
    Card: {
      baseStyle: {
        container: {
          bg: 'white',
          borderRadius: 'xl',
          boxShadow: 'sm',
          border: '1px solid',
          borderColor: 'sand.200',
          overflow: 'hidden',
        },
        header: {
          paddingTop: 4,
          paddingBottom: 2,
          paddingX: 5,
        },
        body: {
          paddingTop: 2,
          paddingBottom: 4,
          paddingX: 5,
        },
        footer: {
          paddingTop: 2,
          paddingBottom: 4,
          paddingX: 5,
        },
      },
    },
    Input: {
      baseStyle: {
        field: {
          borderColor: 'sand.300',
          _hover: {
            borderColor: 'ocean.400',
          },
          _focus: {
            borderColor: 'ocean.500',
            boxShadow: '0 0 0 1px rgba(31, 111, 139, 0.2)',
          },
        },
      },
      variants: {
        outline: {
          field: {
            bg: 'white',
            borderRadius: 'lg',
          },
        },
        filled: {
          field: {
            bg: 'sand.50',
            borderRadius: 'lg',
            _hover: {
              bg: 'sand.100',
            },
            _focus: {
              bg: 'white',
              borderColor: 'ocean.500',
            },
          },
        },
      },
      sizes: {
        md: {
          field: {
            px: 3.5,
            py: 2.5,
            fontSize: 'md',
            borderRadius: 'lg',
          },
        },
      },
      defaultProps: {
        variant: 'outline',
        size: 'md',
      },
    },
    Drawer: {
      baseStyle: {
        dialog: {
          bg: 'white',
        },
        header: {
          borderBottom: '1px solid',
          borderColor: 'sand.200',
          padding: 5,
        },
        body: {
          padding: 5,
        },
        footer: {
          borderTop: '1px solid',
          borderColor: 'sand.200',
          padding: 5,
        },
      },
    },
    Badge: {
      baseStyle: {
        paddingX: 2,
        paddingY: 0.5,
        borderRadius: 'md',
        fontSize: 'xs',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
      },
      variants: {
        subtle: {
          bg: 'ocean.50',
          color: 'ocean.700',
        },
        solid: {
          bg: 'ocean.500',
          color: 'white',
        },
        outline: {
          borderWidth: '1px',
          borderColor: 'ocean.500',
          color: 'ocean.500',
        },
      },
    },
  },
  config: {
    initialColorMode: 'light',
    useSystemColorMode: false,
  },
  space: {
    px: '1px',
    0.5: '0.125rem',
    1: '0.25rem',
    1.5: '0.375rem',
    2: '0.5rem',
    2.5: '0.625rem',
    3: '0.75rem',
    3.5: '0.875rem',
    4: '1rem',
    5: '1.25rem',
    6: '1.5rem',
    7: '1.75rem',
    8: '2rem',
    9: '2.25rem',
    10: '2.5rem',
    12: '3rem',
    14: '3.5rem',
    16: '4rem',
    20: '5rem',
    24: '6rem',
    28: '7rem',
    32: '8rem',
    36: '9rem',
    40: '10rem',
  },
  radii: {
    none: '0',
    sm: '0.125rem',
    base: '0.25rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    '2xl': '1.5rem',
    '3xl': '2rem',
    full: '9999px',
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    base: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  },
});

export default theme;