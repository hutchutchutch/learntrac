# Variables for LLM Integration

variable "openai_api_key" {
  description = "OpenAI API key for LLM services"
  type        = string
  default     = ""
  sensitive   = true
}

variable "llm_model_name" {
  description = "OpenAI model to use for LLM operations"
  type        = string
  default     = "gpt-4"
}

variable "llm_max_tokens" {
  description = "Maximum tokens for LLM responses"
  type        = string
  default     = "1000"
}

variable "llm_temperature" {
  description = "Temperature setting for LLM creativity (0.0-1.0)"
  type        = string
  default     = "0.7"
}