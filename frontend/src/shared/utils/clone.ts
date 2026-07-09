// structuredClone fails on Vue reactive proxies; JSON round-trip strips them safely
export const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T
