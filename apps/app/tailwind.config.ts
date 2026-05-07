import type { Config } from "tailwindcss";

import { lexitorTheme } from "../../packages/ui/theme";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      colors: lexitorTheme.colors,
      fontFamily: lexitorTheme.fontFamily,
    },
  },
  plugins: [],
};

export default config;
