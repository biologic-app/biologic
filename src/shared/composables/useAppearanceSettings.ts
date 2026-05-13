import { ref, watch } from "vue";

const STORAGE_KEY = "appearance-settings";

export type AppFontKey = "onest" | "public-sans" | "system" | "serif";
export type AppFontSizeKey = "sm" | "md" | "lg" | "xl";

interface AppearanceSettings {
  font: AppFontKey;
  fontSize: AppFontSizeKey;
}

export const fontOptions: Array<{
  label: string;
  value: AppFontKey;
  stack: string;
}> = [
  {
    label: "Onest",
    value: "onest",
    stack: '"Onest Variable", sans-serif',
  },
  {
    label: "Public Sans",
    value: "public-sans",
    stack: '"Public Sans", sans-serif',
  },
  {
    label: "System UI",
    value: "system",
    stack: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  {
    label: "Serif",
    value: "serif",
    stack: 'Georgia, "Times New Roman", serif',
  },
];

export const fontSizeOptions: Array<{
  label: string;
  value: AppFontSizeKey;
  size: string;
}> = [
  { label: "14 px", value: "sm", size: "14px" },
  { label: "16 px", value: "md", size: "16px" },
  { label: "18 px", value: "lg", size: "18px" },
  { label: "20 px", value: "xl", size: "20px" },
];

const defaultSettings: AppearanceSettings = {
  font: "onest",
  fontSize: "md",
};

const readSettings = (): AppearanceSettings => {
  if (typeof window === "undefined") {
    return defaultSettings;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw
      ? { ...defaultSettings, ...JSON.parse(raw) }
      : defaultSettings;
  } catch {
    return defaultSettings;
  }
};

const persistSettings = (settings: AppearanceSettings) => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
};

const applySettings = (settings: AppearanceSettings) => {
  if (typeof document === "undefined") {
    return;
  }

  const font = fontOptions.find((item) => item.value === settings.font)
    ?? fontOptions[0];
  const fontSize = fontSizeOptions.find((item) => item.value === settings.fontSize)
    ?? fontSizeOptions[1];

  document.documentElement.style.setProperty("--font-sans", font.stack);
  document.documentElement.style.fontSize = fontSize.size;
  document.body.style.fontFamily = font.stack;
};

export const useAppearanceSettings = () => {
  const stored = readSettings();
  const font = ref<AppFontKey>(stored.font);
  const fontSize = ref<AppFontSizeKey>(stored.fontSize);

  watch(
    [font, fontSize],
    ([nextFont, nextFontSize]) => {
      const settings = { font: nextFont, fontSize: nextFontSize };
      applySettings(settings);
      persistSettings(settings);
    },
    { immediate: true },
  );

  return {
    font,
    fontSize,
    fontOptions,
    fontSizeOptions,
  };
};
