import axios, { AxiosError } from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8001/api/v1"

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError) => {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status
      const message = (error.response.data as { detail?: string })?.detail || error.message

      switch (status) {
        case 401:
          console.error("Unauthorized - Invalid credentials")
          break
        case 403:
          console.error("Forbidden - Insufficient permissions")
          break
        case 404:
          console.error("Resource not found")
          break
        case 500:
          console.error("Internal server error")
          break
        default:
          console.error(`API Error (${status}): ${message}`)
      }
    } else if (error.request) {
      // Request made but no response received
      console.error("Network error - No response from server")
    } else {
      // Error setting up the request
      console.error("Request error:", error.message)
    }

    return Promise.reject(error)
  }
)

export default apiClient
