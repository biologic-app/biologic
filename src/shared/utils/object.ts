export const getValueByPath = (source: Record<string, any>, path: string) =>
  path.split('.').reduce<any>((value, key) => value?.[key], source)
