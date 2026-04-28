"""Layer 1: Vulnerability Detection.

Pipeline (Algorithm 1 in the paper):

    Source/Bytecode
        │
        ▼   Word2Vec semantic preprocessing
    Embeddings + AST
        │
        ▼   Bounded symbolic execution (depth k, default 16)
    Path explorations + assertion violations
        │
        ▼   Rule-based detectors (Slither-style for known SWC patterns)
    Detection Results -> StructuredContext for Layer 2
"""
from belma.detection.symbolic_executor import SymbolicExecutor
from belma.detection.static_analyzer import RuleBasedDetector
from belma.detection.word2vec_preprocessor import Word2VecPreprocessor
from belma.detection.vulnerability_classifier import VulnerabilityClassifier
from belma.detection.detection_pipeline import DetectionPipeline

__all__ = [
    "SymbolicExecutor",
    "RuleBasedDetector",
    "Word2VecPreprocessor",
    "VulnerabilityClassifier",
    "DetectionPipeline",
]
