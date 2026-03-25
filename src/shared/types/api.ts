export interface ApiError {
  status: number
  code?: string
  message: string
}

export interface NamedRef {
  id: number | null
  name: string | null
}
