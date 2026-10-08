class ContractIntelligenceError(Exception):
    """Base error for the contract intelligence pipeline."""


class ConfigurationError(ContractIntelligenceError):
    pass


class IngestionError(ContractIntelligenceError):
    pass


class OCRNotAvailableError(IngestionError):
    pass


class SchemaBoundaryError(ContractIntelligenceError):
    """Raised when an agent emits an object that fails Pydantic validation."""


class RetrievalError(ContractIntelligenceError):
    pass


class LegalKnowledgeError(ContractIntelligenceError):
    pass


class PipelineError(ContractIntelligenceError):
    pass
